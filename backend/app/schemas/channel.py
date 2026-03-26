from pydantic import BaseModel


class ChannelInfo(BaseModel):
    id: str
    title: str
    thumbnail: str | None = None


class PinnedChannelResponse(BaseModel):
    id: str
    channel_id: str
    title: str | None
    thumbnail: str | None

    model_config = {"from_attributes": True}


class PinRequest(BaseModel):
    title: str | None = None
    thumbnail: str | None = None
