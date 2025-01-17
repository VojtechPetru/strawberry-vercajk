__all__ = [
    "BaseIDHasher",
    "HasherType",
    "IDHasher",
    "SingleIDSqids",
]
import abc
import functools
import typing

import pydantic
import pydantic_core
import sqids.sqids
import strawberry
import strawberry.types.scalar

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._id_hasher import exceptions


class HasherType[T](typing.Protocol):
    def encode(self, raw_id: T) -> str: ...

    def decode(self, value: str) -> T: ...


class SingleIDSqids(sqids.Sqids):
    """Wrapper around Sqids to hash only one ID at a time."""

    def encode(self, raw_id: int) -> str:
        return super().encode([raw_id])

    def decode(self, hashed_id: str) -> int:
        decoded_id = super().decode(hashed_id)
        if len(decoded_id) != 1:
            raise ValueError(f"Invalid ID input '{hashed_id}'.")
        return decoded_id[0]


class BaseIDHasher(abc.ABC):
    """Takes care of generating hashed IDs for a given database model and creates a GQL scalar type for it."""

    PREFIX_SEPARATOR: typing.ClassVar[typing.LiteralString] = "_"

    InvalidHashID = exceptions.InvalidHashIDError

    def __init__(self, model: type) -> None:
        from strawberry_vercajk._id_hasher import HashIDRegistry

        if not HashIDRegistry.is_registered(model):
            from strawberry_vercajk._id_hasher import hash_id_register

            raise HashIDRegistry.HashIDNotRegistered(
                f"Hash ID for `{model.__name__}` not registered. "
                f"Please register it using the `@{hash_id_register.__name__}` decorator.",
            )
        self.model = model

    @classmethod
    def gql_scalar_factory(
        cls,
        model: type,
        hash_id_prefix: typing.LiteralString,
        name: typing.LiteralString,
    ) -> type["strawberry.ID"]:
        """Create a GraphQL scalar type for the Hash ID of the given model."""
        hash_id: type[typing.NewType] = strawberry.scalar(
            typing.NewType(name, strawberry.ID),
            serialize=functools.partial(cls._hash_id_serializer, model=model),
            parse_value=functools.partial(cls._hash_id_parser, model=model),
            description=f"""
                ID of `{name}` type.
                This ID is prefixed by `{hash_id_prefix}`,
                for instance `{hash_id_prefix}_abc123def456ghi7`.
            """.strip().replace(
                "\n",
                " ",
            ),
        )
        # Define __get_pydantic_core_schema__ on the type so we can use HashID(...) annotated field in Pydantic models.
        hash_id.__get_pydantic_core_schema__ = cls._scalar_pydantic_core_schema
        typing.cast(type[strawberry.ID], hash_id)
        return hash_id

    def from_hash_id(self, hashed_id: str, /) -> int:
        """Return the model database ID from the given hashed ID."""
        return self._hash_id_parser(hashed_id, model=self.model)

    def to_hash_id(self, id_: int, /) -> str:
        """Return the hashed ID for the given ID."""
        return self._hash_id_serializer(id_, model=self.model)

    @classmethod
    def _hash_id_serializer(cls, id_: int, /, model: type) -> str:
        """Return the hashed ID for the given ID."""
        hasher = cls(model)
        return f"{hasher._hash_id_prefix}{cls.PREFIX_SEPARATOR}{hasher.id_hasher.encode(id_)}"  # noqa: SLF001

    @classmethod
    def _hash_id_parser(
        cls,
        hashed_id: typing.Any,  # noqa: ANN401
        /,
        model: type,
    ) -> int:
        """
        Return the model database ID from the given hashed ID.
        :param hashed_id: Hash ID to parse. This can be "anything" sent by the client, so we need to validate it.
        :param model: Model for which to parse the Hash ID
        :raises InvalidHashIDError: If the given hashed ID is not valid
        """
        from strawberry_vercajk._id_hasher import HashedID

        hashed_id = HashedID(hashed_id)
        hasher = cls(model)
        hasher.validate_hash_id(hashed_id)
        hashed_id = typing.cast(str, hashed_id)  # at this point, we know it's a string (validated above)

        hashid_prefix = f"{hasher._hash_id_prefix}{cls.PREFIX_SEPARATOR}"  # noqa: SLF001
        return hasher.id_hasher.decode(hashed_id.removeprefix(hashid_prefix))

    @staticmethod
    def _scalar_pydantic_core_schema(
        scalar: strawberry.types.scalar.ScalarWrapper,  # noqa: ARG004
        handler: pydantic.GetCoreSchemaHandler,
    ) -> pydantic_core.CoreSchema:
        """
        Defined so that the HashIDUnion scalar is validated in Pydantic models.
        When used in graphql types, we won't get to this point, as the validation will fail earlier (in gql resolver).
        """

        def validate_id(v: int) -> int:
            # No need to validate anything here
            return v

        return pydantic_core.core_schema.no_info_after_validator_function(
            validate_id,
            handler(int),
        )

    @property
    def _hash_id_prefix(self) -> typing.LiteralString:
        """Return the prefix for the Hash ID of this model."""
        from strawberry_vercajk._id_hasher import HashIDRegistry

        return HashIDRegistry.get_model_prefix(self.model)

    @property
    @abc.abstractmethod
    def id_hasher(self) -> HasherType: ...

    def validate_hash_id(
        self,
        hashed_id: typing.Any,  # noqa: ANN401
    ) -> None:
        """
        Validate the correctness of the given hashed ID for this model.
        :raises InvalidHashIDError: If the given hashed ID is not valid
        """
        from strawberry_vercajk._id_hasher import HashIDRegistry

        gql_scalar_name = HashIDRegistry.get_model_gql_scalar_name(self.model)
        if not isinstance(hashed_id, str):
            raise self.InvalidHashID(
                f"Invalid ID '{hashed_id}' ({type(hashed_id).__name__}) for type '{gql_scalar_name}'"
                f" - should be a string.",
            )

        hashed_id_prefix: str = hashed_id.split(self.PREFIX_SEPARATOR)[0]
        if not HashIDRegistry.get_model_by_prefix(hashed_id_prefix):
            raise self.InvalidHashID(
                f"Invalid ID '{hashed_id}' for type '{gql_scalar_name}' - "
                f"prefix '{hashed_id_prefix}' is not a valid prefix.",
            )

        if hashed_id.startswith(self._hash_id_prefix):
            hash_id_length = len(hashed_id.removeprefix(f"{self._hash_id_prefix}{self.PREFIX_SEPARATOR}"))
            if hash_id_length < app_settings.ID_HASHER.MIN_LENGTH:
                raise self.InvalidHashID(f"Invalid ID '{hashed_id}' for type '{gql_scalar_name}'.")
            return
        # Hash ID is valid, but for a different model -> raise error with more info
        from strawberry_vercajk._id_hasher import HashIDRegistry

        error_msg = f"Invalid ID input - '{hashed_id}' is not a {gql_scalar_name}."
        other_model = HashIDRegistry.get_model_by_prefix(hashed_id_prefix)
        if other_model:
            error_msg += f" Received {HashIDRegistry.get_model_gql_scalar_name(other_model)} instead."
        raise self.InvalidHashID(error_msg)


class IDHasher(BaseIDHasher):
    @classmethod
    def __get_cls_id_hasher(cls) -> SingleIDSqids:
        attr: str = "__cls_id_hasher__"
        if id_hasher := getattr(cls, attr, None):
            return id_hasher
        setattr(
            cls,
            attr,
            SingleIDSqids(
                alphabet=app_settings.ID_HASHER.ALPHABET,
                min_length=app_settings.ID_HASHER.MIN_LENGTH,
            ),
        )
        return getattr(cls, attr)

    @property
    def id_hasher(self) -> SingleIDSqids:
        return self.__get_cls_id_hasher()
