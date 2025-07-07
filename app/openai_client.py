import json
import asyncio
import logging
from typing import Dict, List, Optional

from openai import Timeout, APIConnectionError
from openai import AsyncOpenAI, APIError, AuthenticationError, RateLimitError

from app.models import Trip
from app.schemas import TripCreateRequest, TripTypeEnum
from app.trip_prompts import TRIP_PROMPT_SEVERAL_PLACES, TRIP_PROMPT_SINGLE_PLACE

logger = logging.getLogger(__name__)


class ChatGPTError(Exception):
    """Custom exception for ChatGPT errors."""

    pass


TRIP_TYPE = {
    TripTypeEnum.several_places: TRIP_PROMPT_SEVERAL_PLACES,
    TripTypeEnum.by_place: TRIP_PROMPT_SINGLE_PLACE,
}


class OpenAIChatClientBase:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo-1106",
        trip_type: str = "several_places",
    ):
        logger.info("Initializing OpenAI client...")
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)
        self.messages = []
        logger.info("OpenAI client initialized with model: %s", self.model)
        self.system_prompt = TRIP_TYPE.get(trip_type, TRIP_PROMPT_SEVERAL_PLACES)

    def add_message(self, role: str, content: str):
        """Add a message to the chat history."""
        self.messages.append({"role": role, "content": content})

    async def test_credentials(self) -> bool:
        """Test if the OpenAI API credentials are valid."""
        try:
            logger.info("Testing OpenAI credentials with model: %s", self.model)
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "Test OpenAI credentials"}],
            )
            if completion and completion.choices:
                logger.info("OpenAI credentials test successful")
                logger.info(
                    "OpenAI response: %s",
                    completion.choices[0].message.content,
                )
                return True
            return False
        except AuthenticationError as e:
            logger.error("Authentication failed: %s", str(e))
            return False
        except APIError as e:
            logger.error("API error: %s", str(e))
            return False
        except RateLimitError as e:
            logger.error("Rate limit exceeded: %s", str(e))
            return False
        except ChatGPTError as e:
            logger.error("Unexpected error: %s", str(e), exc_info=True)
            return False


class OpenAIChatClientTrip(OpenAIChatClientBase):
    def __init__(self, *args, **kwargs):  # noqa: E501
        super().__init__(*args, **kwargs)
        self.add_message("system", self.system_prompt)

    async def get_completions_create_response(
        self, num_places: Optional[int]
    ) -> Optional[str]:
        """Get a response from OpenAI completions.create with retry support.
        Returns None if all retries fail.
        """
        max_retries = 4
        backoff_base = 1
        max_wait = 8

        for attempt in range(max_retries):
            try:
                logger.debug(
                    "Attempt %d: Starting OpenAI completions.create",
                    attempt,
                )
                completion = await self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    response_format={"type": "json_object"},
                    temperature=0.7,
                )
                logger.debug("OpenAI response received")
                result = completion.choices[0].message.content
                if num_places and len(result) < num_places:
                    logger.warning(
                        "Received response with fewer locations than requested: %d < %d",
                        len(result),
                        num_places,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.debug("OpenAI response content: %s", result)
                    return result

            except (RateLimitError, Timeout, APIConnectionError, APIError) as e:
                wait_time = min(backoff_base * (2**attempt), max_wait)
                logger.warning(
                    "OpenAI request failed with %s (attempt %d/%d). Retrying in %s seconds...",  # noqa: E501
                    type(e).__name__,
                    attempt + 1,
                    max_retries,
                    wait_time,
                    exc_info=True,
                )
                await asyncio.sleep(wait_time)
            except ChatGPTError as e:
                logger.error(
                    "Unexpected error in get_completions_create_response: %s",
                    str(e),
                    exc_info=True,
                )
                return None

        logger.error("All retries failed. Could not get OpenAI completion response.")
        return None

    async def get_trip_prediction(
        self,
        trip: TripCreateRequest,
        trip_type: TripTypeEnum = TripTypeEnum.several_places,
    ) -> List[Optional[Dict]]:
        """Get trip prediction based on the text."""
        try:
            logger.debug("Starting trip prediction for text: %s", trip.request_text)
            req_text = f"Generate location details for: {trip.request_text}"
            if trip.start_location:
                req_text += f" {trip.start_location}"
            if trip.num_places and not trip_type == TripTypeEnum.several_places:
                req_text += f", num_places = {trip.num_places}"
            req_text += ". Return a list of all locations in the order they should be visited."  # noqa: E501

            self.add_message("user", req_text)
            logger.debug("Messages to send: %s", self.messages)

            response_text = await self.get_completions_create_response(
                num_places=trip.num_places
            )
            logger.debug("Raw OpenAI response: %s", response_text)

            return self.parse_response(response_text)

        except ChatGPTError as e:
            logger.error("Error in get_trip_prediction: %s", str(e), exc_info=True)
            return []
        finally:
            # Clear the user message for the next request
            if len(self.messages) > 1:
                self.messages.pop()

    def parse_response(self, response_text: str) -> List[Optional[Dict]]:
        """Parse the OpenAI response text into a list of locations."""
        # Parse the JSON response
        try:
            locations = json.loads(response_text)
            if isinstance(locations, dict) and "locations" in locations:
                locations = locations["locations"]
            if isinstance(locations, dict):
                locations = [locations]
            logger.info("Generated %s locations after exclusion", len(locations))
            logger.debug("Processed locations after exclusion: %s", locations)
            return locations
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", e)
            return []

    async def get_exlude_locations_prediction(
        self, previous_trip: Trip, exclude_text: str
    ) -> List[Optional[Dict]]:
        """Get trip prediction excluding specific locations."""
        try:
            logger.debug(
                "Starting exclusion prediction for text: %s, excluding: %s",
                previous_trip.response_json,
                exclude_text,
            )
            self.add_message(
                "user", f"Previous generated trip was: {previous_trip.response_json}"
            )  # noqa: E501

            self.add_message("user", f"Exclude text: {exclude_text}")
            num_places_text = ""
            if (
                previous_trip.num_places
                and previous_trip.trip_type == TripTypeEnum.by_place
            ):
                num_places_text += f". num_places = {previous_trip.num_places}"
            num_places_text += ". Return a list of all locations in the order they should be visited."  # noqa: E501
            self.add_message("user", num_places_text)

            logger.debug("Messages to send: %s", self.messages)

            response_text = await self.get_completions_create_response()
            logger.debug("Raw OpenAI response: %s", response_text)

            return self.parse_response(response_text)

        except ChatGPTError as e:
            logger.error(
                "Error in get_exlude_locations_prediction: %s",
                str(e),
                exc_info=True,  # noqa: E501
            )
            return []
        finally:
            if len(self.messages) > 2:
                self.messages.pop()
                self.messages.pop()
