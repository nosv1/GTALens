import Database


class Creator:
    def __init__(
            self,
            _id: str = "",
            name: str = "",
    ):
        self._id = _id
        self.name = name

    @property
    def id(self):
        return self._id


def get_creator(_id: str):
    db = Database.connect_database()
    db.cursor.execute(f"SELECT * FROM members WHERE _id = '{_id}'")
    _ = db.cursor.fetchall()[0]
    return Creator(
        _id=_[0],
        name=_[1]
    )

