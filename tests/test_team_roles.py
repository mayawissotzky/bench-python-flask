from tally.teams.directory import leaves_team_without_manager


def test_removing_the_only_manager_is_blocked():
    assert leaves_team_without_manager([1], 1)


def test_demoting_one_of_two_managers_is_allowed():
    assert not leaves_team_without_manager([1, 2], 1, "member")


def test_promoting_a_member_is_allowed():
    assert not leaves_team_without_manager([1], 5, "manager")


def test_removing_a_regular_member_is_allowed():
    assert not leaves_team_without_manager([1], 5)


def test_demoting_the_only_manager_is_blocked():
    assert leaves_team_without_manager([1], 1, "member")
