import functools
import typing


def hash_id_register[T: object](
    prefix: typing.LiteralString,
    *,
    gql_scalar_name: typing.LiteralString | None = None,
) -> typing.Callable[[type[T]], type[T]]:
    """
    Decorator to register a model with a Hash ID GQL scalar type.

    Example:
    -------
        @hash_id_register("user")
        class User(django.db.models.Model):
            ...

    """

    @functools.wraps(hash_id_register)
    def wrapper(
        model: type[T],
    ) -> type[T]:
        from strawberry_vercajk._id_hasher import HashIDRegistry

        # The _register method is marked as private. This decorator is the recommended way to register a model
        #  -> HashIDRegistry._register should not be used directly except for here.
        HashIDRegistry._register(model, prefix, gql_scalar_name=gql_scalar_name)  # noqa: SLF001
        return model

    return wrapper
