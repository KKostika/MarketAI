from sqlmodel import SQLModel, Field

class UserStock(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    stock_id: int = Field(foreign_key="stock.id", primary_key=True)

