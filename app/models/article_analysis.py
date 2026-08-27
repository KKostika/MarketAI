# from __future__ import annotations
# from sqlmodel import SQLModel, Field, Relationship
# from datetime import datetime

# class ArticleAnalysis(SQLModel, table=True):
#     id: int | None = Field(default=None, primary_key=True)
#     article_id: int = Field(foreign_key="article.id")

#     article: "Article" = Relationship(
#         back_populates="analysis",
#         sa_relationship_kwargs={"uselist": False}
#     )

#     sentiment_score: float | None = None
#     summary: str | None = None
#     created_at: datetime = Field(default_factory=datetime.utcnow)

