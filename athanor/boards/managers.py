import re
from django.db import models
from django.conf import settings
from evennia.typeclasses.managers import TypeclassManager, TypedObjectManager
from evennia.utils import class_from_module

from athanor.utils import Request, validate_name

_RE_ABBREV = re.compile(r"^[a-zA-Z]{1,10}$")

_RE_BOARDID = re.compile(r"(?P<collection>[a-zA-Z]{1,10})?(?P<order>\d+)")


class BoardDBManager(TypedObjectManager):
    system_name = "BBS"

    def with_board_id(self):
        return self.annotate(
            board_id=models.Concat(
                models.F("db_collection__db_abbreviation"),
                models.F("db_order"),
                output_field=models.CharField(),
            )
        )

    def prepare_kwargs(self, request: Request):
        pass

    def _validate_name(self, request: Request):
        if not (
            name := validate_name(request.kwargs.get("name", None), thing_type="Board")
        ):
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex("You must provide a name for the board.")
        return name

    def op_create(self, request: Request):
        col_class = class_from_module(settings.BASE_BOARD_COLLECTION_TYPECLASS)
        collection = col_class.objects.find_collection(request)

        caller = request.character or request.user

        if not collection.access(caller, "admin"):
            request.status = request.st.HTTP_401_UNAUTHORIZED
            raise request.ex(
                "You do not have permission to create a board in this collection."
            )

        if (order := request.kwargs.get("order", None)) is None:
            result = collection.boards.aggregate(models.Max("db_order"))
            max_result = result["db_order__max"]
            order = max_result + 1 if max_result is not None else 1
        else:
            try:
                order = int(order)
            except ValueError:
                request.status = request.st.HTTP_400_BAD_REQUEST
                raise request.ex("You must provide a valid order number.")
            if collection.boards.filter(db_order=order).first():
                request.status = request.st.HTTP_400_BAD_REQUEST
                raise request.ex(f"A board with order {order} already exists.")

        name = self._validate_name(request)

        if self.model.objects.filter(db_key__iexact=name).first():
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex(f"A board with the name '{name}' already exists.")

        board = self.create(db_collection=collection, db_order=order, db_key=name)
        request.status = request.st.HTTP_201_CREATED
        request.results = {"success": True, "created": board.serialize()}


class CollectionDBManager(TypedObjectManager):
    system_name = "BBS"

    def prepare_kwargs(self, request: Request):
        pass

    def _validate_abbreviation(self, request: Request):
        abbreviation = request.kwargs.get("abbreviation", None)
        if abbreviation != "" and not (
            abbreviation := validate_name(
                request.kwargs.get("abbreviation", None),
                thing_type="Board Collection",
                matcher=_RE_ABBREV,
            )
        ):
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex(
                "You must provide an abbreviation for the board collection."
            )
        return abbreviation

    def _validate_name(self, request: Request):
        if not (
            name := validate_name(
                request.kwargs.get("name", None), thing_type="Board Collection"
            )
        ):
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex("You must provide a name for the board collection.")
        return name

    def op_create(self, request: Request):
        if not request.user.is_admin():
            request.status = request.st.HTTP_401_UNAUTHORIZED
            raise request.ex("You do not have permission to create a board collection.")

        name = self._validate_name(request)

        if self.model.objects.filter(db_key__iexact=name).first():
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex(
                f"A board collection with the name '{name}' already exists."
            )

        abbreviation = self._validate_abbreviation(request)

        if self.model.objects.filter(db_abbreviation__iexact=abbreviation).first():
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex(
                f"A board collection with the abbreviation '{abbreviation}' already exists."
            )

        collection = self.create(db_key=name, db_abbreviation=abbreviation)
        request.results = {"success": True, "created": collection.serialize()}

    def op_delete(self, request: Request):
        if not request.user.is_admin():
            request.status = request.st.HTTP_401_UNAUTHORIZED
            raise request.ex("You do not have permission to delete a board collection.")

    def find_collection(self, request: Request) -> "BoardCollectionDB":
        if (input := request.kwargs.get("collection_id", None)) is None:
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex("You must provide a Board Collection ID.")

        collection_id = input.strip()

        if isinstance(collection_id, str) and collection_id.isnumeric():
            collection_id = int(collection_id)

        if isinstance(collection_id, int):
            if not (found := self.filter(id=collection_id).first()):
                request.status = request.st.HTTP_404_NOT_FOUND
                raise request.ex(f"No board collection found with ID {collection_id}.")
            return found

        if found := self.filter(db_key__iexact=collection_id).first():
            return found
        elif found := self.filter(db_abbreviation__iexact=collection_id).first():
            return found

        request.status = request.st.HTTP_404_NOT_FOUND
        raise request.ex(f"No board collection found with ID {collection_id}.")

    def op_rename(self, request: Request):
        if not request.user.is_admin():
            request.status = request.st.HTTP_401_UNAUTHORIZED
            raise request.ex("You do not have permission to rename a board collection.")

        collection = self.find_collection(request)

        name = self._validate_name(request)

        if self.filter(db_key__iexact=name).exclude(id=collection).first():
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex(
                f"A board collection with the name '{name}' already exists."
            )

        collection.key = name
        request.results = {"success": True, "renamed": name}

    def op_abbreviate(self, request: Request):
        if not request.user.is_admin():
            request.status = request.st.HTTP_401_UNAUTHORIZED
            raise request.ex(
                "You do not have permission to re-abbreviate a board collection."
            )

        collection = self.find_collection(request)

        abbreviation = self._validate_abbreviation(request)

        if (
            self.filter(db_abbreviation__iexact=abbreviation)
            .exclude(id=collection)
            .first()
        ):
            request.status = request.st.HTTP_400_BAD_REQUEST
            raise request.ex(
                f"A board collection with the abbreviation '{abbreviation}' already exists."
            )

        collection.abbreviation = abbreviation
        request.results = {"success": True, "abbreviated": abbreviation}

    def op_lock(self, request: Request):
        if not request.user.is_admin():
            request.status = request.st.HTTP_401_UNAUTHORIZED
            raise request.ex("You do not have permission to lock a board collection.")

        collection = self.find_collection(request)

    def op_config(self, request: Request):
        if not request.user.is_admin():
            request.status = request.st.HTTP_401_UNAUTHORIZED
            raise request.ex("You do not have permission to config a board collection.")

        collection = self.find_collection(request)


class BoardManager(BoardDBManager, TypeclassManager):
    pass


class CollectionManager(CollectionDBManager, TypeclassManager):
    system_name = "BBS"
