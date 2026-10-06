import pytest

from habits import service
from tests.conftest import ALICE, BOB

DAY = "2026-09-30"


def test_log_checkin_counts_up(db):
    hid = service.create_habit(db, ALICE, "Read", target_count_per_day=2)
    assert service.log_checkin(db, ALICE, hid, DAY) == 1
    assert service.log_checkin(db, ALICE, hid, DAY) == 2
    assert service.log_checkin(db, ALICE, hid, DAY) == 3


def test_checkins_are_per_day(db):
    hid = service.create_habit(db, ALICE, "Read")
    service.log_checkin(db, ALICE, hid, "2026-09-29")
    assert service.log_checkin(db, ALICE, hid, DAY) == 1


def test_undo_checkin_floors_at_zero(db):
    hid = service.create_habit(db, ALICE, "Read")
    service.log_checkin(db, ALICE, hid, DAY)
    assert service.undo_checkin(db, ALICE, hid, DAY) == 0
    assert service.undo_checkin(db, ALICE, hid, DAY) == 0


def test_undo_checkin_without_row_returns_zero(db):
    hid = service.create_habit(db, ALICE, "Read")
    assert service.undo_checkin(db, ALICE, hid, DAY) == 0


def test_other_user_cannot_checkin_or_undo(db):
    hid = service.create_habit(db, ALICE, "Read")
    with pytest.raises(ValueError):
        service.log_checkin(db, BOB, hid, DAY)
    with pytest.raises(ValueError):
        service.undo_checkin(db, BOB, hid, DAY)


def test_other_user_cannot_archive(db):
    hid = service.create_habit(db, ALICE, "Read")
    service.archive_habit(db, BOB, hid)
    assert [h["id"] for h in service.list_habits(db, ALICE)] == [hid]


def test_archive_hides_habit(db):
    hid = service.create_habit(db, ALICE, "Read")
    service.archive_habit(db, ALICE, hid)
    assert service.list_habits(db, ALICE) == []


def test_list_habits_is_ordered_and_scoped(db):
    first = service.create_habit(db, ALICE, "A")
    second = service.create_habit(db, ALICE, "B")
    service.create_habit(db, BOB, "Not Alice's")
    assert [h["id"] for h in service.list_habits(db, ALICE)] == [first, second]


@pytest.mark.parametrize("kwargs", [
    {"target_count_per_day": 0},
    {"frequency": "weekly"},
    {"frequency": "custom"},
    {"frequency": "custom", "weekdays_mask": 0},
    {"frequency": "custom", "weekdays_mask": 128},
])
def test_create_habit_rejects_invalid_settings(db, kwargs):
    with pytest.raises(ValueError):
        service.create_habit(db, ALICE, "Bad", **kwargs)


def test_create_custom_habit(db):
    hid = service.create_habit(db, ALICE, "Gym", frequency="custom", weekdays_mask=0b10101)
    habit = service.list_habits(db, ALICE)[0]
    assert habit["id"] == hid and habit["weekdays_mask"] == 0b10101


def test_create_group_appends_positions(db):
    a = service.create_group(db, ALICE, "Morning")
    b = service.create_group(db, ALICE, "Evening")
    service.create_group(db, BOB, "Not Alice's")
    groups = service.list_groups(db, ALICE)
    assert [g["id"] for g in groups] == [a, b]
    assert [g["position"] for g in groups] == [0, 1]


def test_create_group_requires_name(db):
    with pytest.raises(ValueError):
        service.create_group(db, ALICE, "   ")


def test_create_habit_in_group_and_filter(db):
    gid = service.create_group(db, ALICE, "Morning")
    in_group = service.create_habit(db, ALICE, "Stretch", group_id=gid)
    service.create_habit(db, ALICE, "Read")
    assert [h["id"] for h in service.list_habits(db, ALICE, group_id=gid)] == [in_group]
    assert len(service.list_habits(db, ALICE)) == 2


def test_set_habit_group_moves_and_ungroups(db):
    gid = service.create_group(db, ALICE, "Morning")
    hid = service.create_habit(db, ALICE, "Read")
    service.set_habit_group(db, ALICE, hid, gid)
    assert service.list_habits(db, ALICE, group_id=gid)[0]["id"] == hid
    service.set_habit_group(db, ALICE, hid, None)
    assert service.list_habits(db, ALICE, group_id=gid) == []


def test_cannot_use_another_users_group(db):
    bobs_group = service.create_group(db, BOB, "Bob's")
    hid = service.create_habit(db, ALICE, "Read")
    with pytest.raises(ValueError):
        service.create_habit(db, ALICE, "Run", group_id=bobs_group)
    with pytest.raises(ValueError):
        service.set_habit_group(db, ALICE, hid, bobs_group)
    with pytest.raises(ValueError):
        service.set_habit_group(db, BOB, hid, bobs_group)


def test_delete_group_keeps_habits_ungrouped(db):
    gid = service.create_group(db, ALICE, "Morning")
    hid = service.create_habit(db, ALICE, "Read", group_id=gid)
    service.delete_group(db, ALICE, gid)
    assert service.list_groups(db, ALICE) == []
    assert service.list_habits(db, ALICE)[0]["group_id"] is None


def test_other_user_cannot_delete_group(db):
    gid = service.create_group(db, ALICE, "Morning")
    service.delete_group(db, BOB, gid)
    assert len(service.list_groups(db, ALICE)) == 1


def test_checkins_by_date(db):
    hid = service.create_habit(db, ALICE, "Read")
    service.log_checkin(db, ALICE, hid, "2026-09-29")
    service.log_checkin(db, ALICE, hid, DAY)
    service.log_checkin(db, ALICE, hid, DAY)
    assert service.checkins_by_date(db, hid) == {"2026-09-29": 1, DAY: 2}
