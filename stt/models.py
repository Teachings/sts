from pydantic import BaseModel, Field
from typing import List

class TranscriptionSegment(BaseModel):
    timestamp: str = Field(..., description="Timestamp of the transcription")
    text: str = Field(..., description="Text of the transcription")

class TranscriptionData(BaseModel):
    transcriptions: List[TranscriptionSegment] = Field(default_factory=list)