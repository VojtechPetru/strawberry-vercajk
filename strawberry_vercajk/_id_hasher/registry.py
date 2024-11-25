import functools
import textwrap
import typing
from types import UnionType

import pydantic
import pydantic_core
import strawberry
import strawberry.types.scalar

from strawberry_vercajk._id_hasher import exceptions

if typing.TYPE_CHECKING:
    from strawberry_vercajk._id_hasher import IDHasher


class HashIDRegistry:
    """
    Registers GQL scalar types of model hashed IDs.
    """

    _REGISTRY: typing.ClassVar[dict[type, type[strawberry.ID]]] = {}
    _PREFIX_TO_MODEL_REGISTRY: typing.ClassVar[dict[str, type]] = {}
    _MODEL_TO_PREFIX_REGISTRY: typing.ClassVar[dict[type, str]] = {}
    _MODEL_TO_GQL_SCALAR_NAME_REGISTRY: typing.ClassVar[dict[type, str]] = {}

    # Exceptions
    HashIDNotRegistered = exceptions.HashIDNotRegisteredError
    InvalidHashID = exceptions.InvalidHashIDError
    InvalidHashIDPrefix = exceptions.InvalidHashIDPrefixError
    HashIDAlreadyRegistered = exceptions.HashIDAlreadyRegisteredError

    @classmethod
    def get(cls, model: type) -> type[strawberry.ID]:
        if model not in cls._REGISTRY:
            from strawberry_vercajk._id_hasher import hash_id_register

            raise cls.HashIDNotRegistered(
                f"Hash ID for `{model.__name__}` not registered. Register it "
                f"using the `@{hash_id_register.__name__}` decorator.",
            )
        return cls._REGISTRY[model]

    @classmethod
    def _register(
        cls,
        model: type,
        hash_id_prefix: typing.LiteralString,
        gql_scalar_name: typing.LiteralString | None = None,
    ) -> None:
        """
        Register the Hash ID GQL scalar type for a given model.
        This is a private method, use the model decorator instead.
        """
        if gql_scalar_name is None:
            gql_scalar_name = typing.cast(typing.LiteralString, f"{model.__name__}ID")
        cls._pre_registration_checks(model, hash_id_prefix, gql_scalar_name)

        from strawberry_vercajk._id_hasher import IDHasher

        cls._REGISTRY[model] = IDHasher.gql_scalar_factory(model, hash_id_prefix, name=gql_scalar_name)
        cls._PREFIX_TO_MODEL_REGISTRY[hash_id_prefix] = model
        cls._MODEL_TO_PREFIX_REGISTRY[model] = hash_id_prefix
        cls._MODEL_TO_GQL_SCALAR_NAME_REGISTRY[model] = gql_scalar_name

    @classmethod
    def is_registered(cls, model: type) -> bool:
        """Return whether the given model is registered with a Hash ID GQL scalar type."""
        return model in cls._REGISTRY

    @classmethod
    def get_model_by_prefix(cls, prefix: str) -> type | None:
        """
        Return the model whose Hash ID prefix is the given one.
        """
        return cls._PREFIX_TO_MODEL_REGISTRY.get(prefix)

    @classmethod
    def get_hasher_by_hash_id(cls, hash_id: str) -> "IDHasher":
        """
        Return the Hasher whose Hash ID is the given one.
        """
        from strawberry_vercajk._id_hasher import IDHasher

        split_hash = hash_id.split(IDHasher.PREFIX_SEPARATOR)
        if not len(split_hash) == 2:  # noqa: PLR2004
            raise cls.InvalidHashID(f"Invalid Hash ID `{hash_id}`.")
        model = cls.get_model_by_prefix(split_hash[0])
        if not model:
            raise cls.HashIDNotRegistered(f"Hash ID `{hash_id}` not registered.")
        return IDHasher(model)

    @classmethod
    def get_model_prefix(cls, model: type) -> typing.LiteralString | None:
        """Return the Hash ID prefix for the given model."""
        return cls._MODEL_TO_PREFIX_REGISTRY.get(model)

    @classmethod
    def get_model_gql_scalar_name(cls, model: type) -> typing.LiteralString | None:
        """Return the Hash ID GQL scalar name for the given model."""
        return cls._MODEL_TO_GQL_SCALAR_NAME_REGISTRY.get(model)

    @classmethod
    def get_model_from_gql_scalar_name(
        cls,
        gql_scalar_name: typing.LiteralString,
    ) -> type | None:
        """Return the model whose Hash ID GQL scalar name is the given one."""
        mapping: dict[str, type] = {v: k for k, v in cls._MODEL_TO_GQL_SCALAR_NAME_REGISTRY.items()}
        return mapping.get(gql_scalar_name)

    @classmethod
    def _pre_registration_checks(
        cls,
        model: type,
        hash_id_prefix: typing.LiteralString,
        gql_scalar_name: typing.LiteralString,
    ) -> None:
        """Check whether the given model can be registered with the given Hash ID prefix and GQL scalar name."""
        if not hash_id_prefix.islower() or not hash_id_prefix.isalpha():
            raise cls.InvalidHashIDPrefix(
                f"Hash ID prefix `{hash_id_prefix}` must be lowercase and alphabetical.",
            )
        if model in cls._REGISTRY:
            raise cls.HashIDAlreadyRegistered(f"Hash ID for `{model.__name__}` already registered.")
        if _registered := cls.get_model_by_prefix(hash_id_prefix):  # noqa: SIM102
            if _registered != model:
                raise cls.HashIDAlreadyRegistered(
                    f"Can't register hash ID prefix `{hash_id_prefix}` for a model `{model.__name__}`,\n"
                    f"because it is already registered for `{_registered.__name__}`.",
                )

        if _registered := cls.get_model_from_gql_scalar_name(gql_scalar_name):
            from strawberry_vercajk._id_hasher import hash_id_register

            raise cls.HashIDAlreadyRegistered(
                f"Can't register `{model.__name__}` with hash ID GQL scalar name `{gql_scalar_name}`, because\n"
                f"it is already used by `{_registered.__name__}`. "
                f"Please choose another name using `gql_scalar_name` argument in\n"
                f"the `@{hash_id_register.__name__}` decorator.",
            )


def _hashed_id_pydantic_core_schema(
    hashed_id: "HashedID",  # noqa: ARG001
    handler: pydantic.GetCoreSchemaHandler,
) -> pydantic_core.CoreSchema:
    def validate_hashed_id(v: str) -> "HashedID":
        try:
            HashIDRegistry.get_hasher_by_hash_id(v)
        except (HashIDRegistry.InvalidHashID, HashIDRegistry.HashIDNotRegistered) as e:
            raise pydantic_core.PydanticCustomError(
                "invalid_id",
                "Invalid ID {hashed_id}.",
                {
                    "hashed_id": v,
                },
            ) from e
        return HashedID(v)

    return pydantic_core.core_schema.no_info_after_validator_function(
        validate_hashed_id,
        handler(str),
    )


class HashedID[T: type | ...](str):  # noqa: SLOT000
    """
    Represents a hashed ID of an object (see IDHasher).
    """

    @functools.cached_property
    def hasher(self) -> "IDHasher":
        return HashIDRegistry.get_hasher_by_hash_id(self)

    @functools.cached_property
    def id(self) -> int:
        return self.hasher.from_hash_id(self)

    @property
    def model(self) -> type[T]:
        return self.hasher.model


# Allows HashedID to be used as a field type in Pydantic models.
HashedID.__get_pydantic_core_schema__ = _hashed_id_pydantic_core_schema


class HashIDUnionRegistry:
    _REGISTRY: typing.ClassVar[dict[str, type["_HashIDUnion"]]] = {}

    @classmethod
    def get_gql_scalar[T: UnionType](cls, types: T) -> type["HashIDUnion[T]"]:
        models = typing.get_args(types)
        id_scalar_names = cls._get_id_scalar_names(models)
        gql_scalar_name = "IDUnion" if id_scalar_names is None else "".join(id_scalar_names) + "Union"
        if gql_scalar_name in cls._REGISTRY:
            return cls._REGISTRY[gql_scalar_name]

        def raise_not_implemented(*args, **kwargs) -> typing.NoReturn:
            raise NotImplementedError("Only parsing is supported.")

        scalar = strawberry.scalar(
            typing.NewType(gql_scalar_name, _HashIDUnion),
            serialize=raise_not_implemented,
            parse_value=functools.partial(cls._parser, models=models),
            description=textwrap.dedent(
                f"""
                Accepts multiple possible types of object IDs.
                Can be any of the following: {', '.join(id_scalar_names)}.
                """,
            ),
        )
        # So we can use HashIDUnion(...) annotated field in Pydantic models.
        scalar.__get_pydantic_core_schema__ = cls._scalar_pydantic_core_schema
        cls._REGISTRY[gql_scalar_name] = scalar
        return cls._REGISTRY[gql_scalar_name]

    @classmethod
    def _get_id_scalar_names(cls, models: typing.Iterable[type]) -> list[str] | None:
        if models is None:
            return None
        if not models:
            raise ValueError("Models must not be empty.")

        scalar_names: list[str] = []
        for model in models:
            hash_id_scalar_name = HashIDRegistry.get_model_gql_scalar_name(model=model)
            if not hash_id_scalar_name:
                raise HashIDRegistry.HashIDNotRegistered(f"Hash ID for `{model.__name__}` not registered.")
            scalar_names.append(hash_id_scalar_name)
        return sorted(scalar_names)

    @classmethod
    def _parser(
        cls,
        value: str,
        /,
        models: set[type] | None,
    ) -> "HashedID":
        hashed_id = HashedID(value)
        if models and hashed_id.model not in models:
            id_scalar_names = cls._get_id_scalar_names(models)
            raise TypeError(f"Hash ID `{hashed_id}` is not one of the allowed ID types ({', '.join(id_scalar_names)}).")
        return hashed_id

    @staticmethod
    def _scalar_pydantic_core_schema(
        scalar: strawberry.types.scalar.ScalarWrapper,
        handler: pydantic.GetCoreSchemaHandler,
    ) -> pydantic_core.CoreSchema:
        """
        Defined so that the HashIDUnion scalar is validated in Pydantic models.
        When used in graphql types, we won't get to this point, as the validation will fail earlier (in gql resolver).
        """

        def validate_id(v: HashedID) -> HashedID:
            v = HashedID(v)
            allowed_models: list[type] = scalar._scalar_definition.parse_value.keywords["models"]  # noqa: SLF001
            if v.model not in allowed_models:
                raise ValueError(f"Hash ID `{v}` is not one of the allowed ID types.")
            return v

        return pydantic_core.core_schema.no_info_after_validator_function(
            validate_id,
            handler(str),
        )


class _HashIDUnion[T: UnionType](HashedID[type[T]]):
    """
    Object which may contain multiple possible types of hashed IDs (see IDHasher).

    This is useful when we need to accept multiple types of object IDs in a single field.
    For example, it's used in file upload fields where we accept IDs of a new file upload (i.e., FileUploadID)
    or an ID of existing file (e.g., EmployeeCertificationDocumentID).
    """

    def __call__(self, types: UnionType) -> "type[_HashIDUnion[type[HashedID[T]]]]":
        return HashIDUnionRegistry.get_gql_scalar(types)


class _HashID:
    """
    A class that allows to use Hash ID GQL scalar types in strawberry - serialize and deserialize values.

    Example usage:
        @strawberry.type()
        class SomeType:
            id: HashID(SomeModel)
            ...

    Optionally, you can also input the database model as a string with the registered prefix, like HashID("<prefix>").
    """

    def __call__(self, model: type | typing.LiteralString) -> type[strawberry.ID]:
        if isinstance(model, str):
            model_prefix = model
            model = HashIDRegistry.get_model_by_prefix(model)
            if not model:
                raise HashIDRegistry.HashIDNotRegistered(f"Hash ID for prefix `{model_prefix}` not registered.")
        return HashIDRegistry.get(model)


HashID = _HashID()
HashIDUnion = _HashIDUnion()
