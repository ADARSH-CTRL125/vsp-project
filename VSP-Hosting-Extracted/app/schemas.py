from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class LoginIn(BaseModel): username:str; password:str
class RegisterIn(BaseModel):
    username:str=Field(min_length=3,max_length=80)
    full_name:str=Field(min_length=2,max_length=160)
    email:str=Field(min_length=5,max_length=254)
    password:str=Field(min_length=8,max_length=128)
class ForgotPasswordIn(BaseModel): email:str=Field(min_length=5,max_length=254)
class ResetPasswordIn(BaseModel): token:str=Field(min_length=20,max_length=200); password:str=Field(min_length=8,max_length=128)
class UserCreate(BaseModel): username:str=Field(min_length=3,max_length=80); full_name:str; password:str=Field(min_length=12); role:Literal["Admin","Staff","Viewer"]; email:str|None=None
class UserOut(BaseModel): id:int; username:str; full_name:str; role:str; active:bool; email:str|None=None
class SupplierIn(BaseModel): name:str; contact:str|None=None; phone:str|None=None; email:str|None=None; address:str|None=None
class CustomerIn(BaseModel): name:str; phone:str|None=None; email:str|None=None; address:str|None=None
class PartIn(BaseModel): name:str; category:str; brand:str; models:str; qty:int=Field(ge=0); reorder:int=Field(ge=0); purchasePrice:Decimal=Field(ge=0); sellingPrice:Decimal=Field(ge=0); supplierId:str|None=None
class LineIn(BaseModel): partId:str; qty:int=Field(gt=0); unitPrice:Decimal=Field(ge=0)
class PurchaseIn(BaseModel): supplierId:str; items:list[LineIn]=Field(min_length=1)
class SaleIn(BaseModel): customerId:str; paymentMode:str; items:list[LineIn]=Field(min_length=1)
class StoreOrderLine(BaseModel): productId:str; qty:int=Field(gt=0,le=50)
class StoreOrderIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); phone:str=Field(min_length=10,max_length=30)
    email:str|None=None; address:str=Field(min_length=5,max_length=500); city:str=Field(min_length=2,max_length=100)
    state:str=Field(min_length=2,max_length=100); pincode:str=Field(min_length=5,max_length=12)
    paymentMode:Literal["Cash on Delivery","UPI"]="Cash on Delivery"; items:list[StoreOrderLine]=Field(min_length=1)
class StoreOrderTrackIn(BaseModel):
    orderId:str=Field(min_length=8,max_length=32); phone:str=Field(min_length=10,max_length=30)
class StoreLeadIn(BaseModel):
    name:str=Field(min_length=2,max_length=160); phone:str=Field(min_length=10,max_length=30)
    vehicle:str=Field(min_length=2,max_length=200); partQuery:str=Field(min_length=2,max_length=300); note:str|None=None
class StoreProductIn(BaseModel):
    name:str=Field(min_length=2,max_length=180); category:str; brand:str; models:str="All models"
    description:str=""; partNumber:str=""; price:Decimal=Field(ge=0); compareAt:Decimal|None=Field(default=None,ge=0)
    stock:int=Field(ge=0); image:str=""; active:bool=True
class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
