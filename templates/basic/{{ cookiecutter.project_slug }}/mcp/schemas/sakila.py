import datetime

from sqlmodel import Field, Relationship, SQLModel


class FilmActorLink(SQLModel, table=True):
    """
    Link table between Films and Actors, representing which actors starred in which films.
    """

    __tablename__ = "film_actor"
    film_id: int | None = Field(
        default=None,
        foreign_key="film.film_id",
        primary_key=True,
        description="Foreign key to the film table.",
    )
    actor_id: int | None = Field(
        default=None,
        foreign_key="actor.actor_id",
        primary_key=True,
        description="Foreign key to the actor table.",
    )
    last_update: datetime.datetime | None = Field(
        default_factory=datetime.datetime.utcnow,
        description="Timestamp of the last update to this link.",
    )


class FilmCategoryLink(SQLModel, table=True):
    """
    Link table between Films and Categories, representing the genre of each film.
    """

    __tablename__ = "film_category"
    film_id: int | None = Field(
        default=None,
        foreign_key="film.film_id",
        primary_key=True,
        description="Foreign key to the film table.",
    )
    category_id: int | None = Field(
        default=None,
        foreign_key="category.category_id",
        primary_key=True,
        description="Foreign key to the category table.",
    )
    last_update: datetime.datetime | None = Field(
        default_factory=datetime.datetime.utcnow,
        alias="Last Update",
        description="Timestamp of the last update to this link.",
    )


class Actor(SQLModel, table=True):
    """
    Represents an actor who can star in films.
    """

    actor_id: int | None = Field(primary_key=True, description="Unique identifier for the actor.")
    first_name: str = Field(alias="First Name", description="The actor's first name.")
    last_name: str = Field(alias="Last Name", description="The actor's last name.")
    last_update: datetime.datetime | None = Field(
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )
    # Relationship to the Film table through the link table
    films: list["Film"] = Relationship(back_populates="actors", link_model=FilmActorLink)


class Category(SQLModel, table=True):
    """
    Represents a category or genre of a film (e.g., Action, Comedy, Horror).
    """

    category_id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the category.")
    name: str = Field(alias="Name", description="The name of the category.")
    last_update: datetime.datetime | None = Field(
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )

    # Relationship to the Film table through the link table
    films: list["Film"] = Relationship(back_populates="categories", link_model=FilmCategoryLink)


class Language(SQLModel, table=True):
    """
    Represents a language in which a film can be.
    """

    __table_args__ = ({"info": {"title": "Language"}},)

    language_id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the language.")
    name: str = Field(alias="Name", description="The name of the language, e.g., 'English', 'Japanese'.")
    last_update: datetime.datetime | None = Field(
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )

    # Relationship: One language can be associated with many films
    films: list["Film"] = Relationship(back_populates="language")


class Film(SQLModel, table=True):
    """
    Represents a film or movie available for rent.
    """

    __table_args__ = ({"info": {"title": "Film"}},)

    film_id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the film.")
    title: str = Field(alias="Title", description="The title of the film.")
    description: str | None = Field(
        default=None, alias="Description", description="A short description or synopsis of the film."
    )
    release_year: int | None = Field(default=None, alias="Release Year", description="The year the film was released.")
    language_id: int = Field(foreign_key="language.language_id", description="Identifier for the film's language.")
    rental_duration: int = Field(
        default=3, alias="Rental Duration", description="The standard number of days the film can be rented for."
    )
    rental_rate: float = Field(default=4.99, alias="Rental Rate", description="The cost to rent the film.")
    length: int | None = Field(default=None, alias="Length (min)", description="The duration of the film in minutes.")
    replacement_cost: float = Field(
        default=19.99,
        alias="Replacement Cost",
        description="The cost to replace the film if it is lost or damaged.",
    )
    rating: str | None = Field(
        default="G", alias="Rating", description="The MPAA rating of the film, e.g., 'G', 'PG', 'R'."
    )
    special_features: str | None = Field(
        default=None,
        alias="Special Features",
        description="Special features included on the DVD, e.g., 'Trailers', 'Deleted Scenes'.",
    )
    last_update: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )

    # Relationships
    language: Language = Relationship(
        back_populates="films", sa_relationship_kwargs={"foreign_keys": "[Film.language_id]"}
    )
    actors: list[Actor] = Relationship(back_populates="films", link_model=FilmActorLink)
    categories: list[Category] = Relationship(back_populates="films", link_model=FilmCategoryLink)


class Country(SQLModel, table=True):
    """
    Represents a country.
    """

    __table_args__ = ({"info": {"title": "Country"}},)

    country_id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the country.")
    country: str = Field(alias="Country", description="The name of the country.")
    last_update: datetime.datetime | None = Field(
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )

    # Relationship: One country can have many cities
    cities: list["City"] = Relationship(back_populates="country")


class City(SQLModel, table=True):
    """
    Represents a city within a country.
    """

    __table_args__ = ({"info": {"title": "City"}},)

    city_id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the city.")
    city: str = Field(alias="City", description="The name of the city.")
    country_id: int = Field(foreign_key="country.country_id", description="Identifier for the associated country.")
    last_update: datetime.datetime | None = Field(
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )

    # Relationships
    country: Country = Relationship(back_populates="cities")
    addresses: list["Address"] = Relationship(back_populates="city")


class Address(SQLModel, table=True):
    """
    Represents a postal address. Used for customers and stores.
    """

    address_id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the address.")
    address: str = Field(alias="Address", description="The main street address line.")
    address2: str | None = Field(
        default=None, alias="Address Line 2", description="Optional second line of the street address."
    )
    district: str = Field(alias="District", description="The district, state, or province.")
    city_id: int = Field(foreign_key="city.city_id", description="Identifier for the associated city.")
    postal_code: str | None = Field(default=None, alias="Postal Code", description="The postal or ZIP code.")
    phone: str = Field(alias="Phone Number", description="The contact phone number for this address.")
    last_update: datetime.datetime | None = Field(
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )

    # Relationships
    city: City = Relationship(back_populates="addresses")
    stores: list["Store"] = Relationship(back_populates="address")


class Store(SQLModel, table=True):
    """
    Represents a physical store location.
    """

    store_id: int | None = Field(default=None, primary_key=True, description="Unique identifier for the store.")
    address_id: int = Field(
        default=None,
        foreign_key="address.address_id",
        description="Identifier for the store's address.",
    )
    last_update: datetime.datetime | None = Field(
        default_factory=datetime.datetime.utcnow,
        alias="Last Update",
        description="Timestamp of the last update to this record.",
    )

    # Relationships
    address: Address = Relationship(back_populates="stores")
