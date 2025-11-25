from pydantic import BaseModel

class ListDonationModel(BaseModel):
    DonationId: int
    DonorName: str
    ReceiverName: str
    Amount: float   
    Message: str = None
    Date: str