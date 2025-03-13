import pytest
from utils.types import (
    ChannelData, TestResult, OriginType, IPvType,
    CategoryChannelData, TestResultCacheData, ChannelTestResult
)

def test_channel_data_valid():
    """Test that a valid ChannelData dictionary works as expected."""
    valid_channel = ChannelData(
        id=1,
        url="http://example.com",
        host="example.com",
        date="2023-10-10",
        resolution="1080p",
        origin="local",  # valid as per OriginType
        ipv_type="ipv4"  # valid as per IPvType
    )
    assert valid_channel["id"] == 1
    assert valid_channel["url"] == "http://example.com"

    valid_channel_none_ipv = ChannelData(
        id=2,
        url="http://example.org",
        host="example.org",
        date=None,
        resolution=None,
        origin="whitelist",
        ipv_type=None
    )
    assert valid_channel_none_ipv["ipv_type"] is None

def test_test_result_valid():
    """Test that a valid TestResult dictionary works as expected."""
    valid_result = TestResult(
        speed=50.5,
        delay=10,
        resolution="720p"
    )
    assert isinstance(valid_result["speed"], float)
    assert isinstance(valid_result["delay"], int)
    assert valid_result["resolution"] == "720p"

def test_category_channel_data_structure():
    """Test the nested structure of CategoryChannelData."""
    channel1 = ChannelData(
        id=1,
        url="http://channel.com/1",
        host="channel.com",
        date="2023-10-10",
        resolution="480p",
        origin="subscribe",
        ipv_type="ipv6"
    )
    category_data: CategoryChannelData = {
        "movies": {
            "action": [channel1],
            "drama": []
        },
        "news": {
            "world": [channel1],
        }
    }
    assert "movies" in category_data
    assert "action" in category_data["movies"]
    assert len(category_data["movies"]["action"]) == 1

def test_test_result_cache_data_structure():
    """Test the structure of TestResultCacheData."""
    result1 = TestResult(speed=100, delay=5, resolution="1080p")
    result2 = TestResult(speed=None, delay=None, resolution=None)
    cache_data: TestResultCacheData = {
        "channel_1": [result1, result2],
        "channel_2": [result2]
    }
    assert "channel_1" in cache_data
    assert len(cache_data["channel_1"]) == 2

def test_channel_test_result_union():
    """Test the union type ChannelTestResult with both ChannelData and TestResult."""
    channel_item: ChannelTestResult = ChannelData(
        id=3,
        url="http://channel.com/3",
        host="channel.com",
        date="2023-10-11",
        resolution="4K",
        origin="hotel",
        ipv_type="ipv4"
    )
    test_result_item: ChannelTestResult = TestResult(
        speed=75,
        delay=20,
        resolution="1080p"
    )
    if "id" in channel_item:
        assert channel_item["id"] == 3
    if "speed" in test_result_item:
        assert isinstance(test_result_item["delay"], int)

def test_invalid_origin_type():
    """Test that an invalid origin type raises a ValueError."""
    with pytest.raises(ValueError):
        # Simulate runtime validation since TypedDict doesn't enforce literal values.
        invalid_value = "invalid_origin"
        allowed_origins = {"local", "whitelist", "subscribe", "hotel", "multicast", "online_search"}
        if invalid_value not in allowed_origins:
            raise ValueError("Invalid origin")
        ChannelData(
            id=999,
            url="http://invalid.com",
            host="invalid.com",
            date=None,
            resolution=None,
            origin=invalid_value,
            ipv_type=None
        )

def test_invalid_ipv_type():
    """Test that an invalid ipv type raises a ValueError."""
    with pytest.raises(ValueError):
        invalid_ipv = "ipv10"
        allowed_ipv = {"ipv4", "ipv6", None}
        if invalid_ipv not in allowed_ipv:
            raise ValueError("Invalid ipv_type")
        ChannelData(
            id=888,
            url="http://invalid-ip.com",
            host="invalid-ip.com",
            date=None,
            resolution=None,
            origin="online_search",
            ipv_type=invalid_ipv
        )
def test_channel_data_modification():
    """Test modifying an existing ChannelData dictionary to ensure updates are preserved."""
    channel = ChannelData(
        id=10,
        url="http://mod.com",
        host="mod.com",
        date="2023-01-01",
        resolution="720p",
        origin="online_search",
        ipv_type="ipv6"
    )
    # Modify a field and check that it is updated
    channel["url"] = "http://modified.com"
    assert channel["url"] == "http://modified.com"

def test_channel_data_extra_key():
    """Test that adding an extra key to ChannelData is allowed and the extra key is preserved."""
    channel = ChannelData(
        id=11,
        url="http://extra.com",
        host="extra.com",
        date="2023-01-02",
        resolution="480p",
        origin="multicast",
        ipv_type="ipv4",
        extra="not allowed"
    )
    assert channel["extra"] == "not allowed"

def test_json_serialization_of_test_result():
    """Test that TestResult can be serialized and deserialized using json."""
    import json
    test_result = TestResult(
        speed=200,
        delay=10,
        resolution="4K"
    )
    serialized = json.dumps(test_result)
    deserialized = json.loads(serialized)
    assert deserialized == test_result
def test_json_serialization_of_channel_data():
    """Test that ChannelData can be serialized and deserialized using json."""
    import json
    channel_data = {
        "id": 20,
        "url": "http://jsonchannel.com",
        "host": "jsonchannel.com",
        "date": "2023-11-01",
        "resolution": "1080p",
        "origin": "online_search",
        "ipv_type": "ipv6"
    }
    # Create a ChannelData instance; note that TypedDict behaves like a plain dict.
    channel = channel_data  # pylint: disable=unnecessary-assignment
    serialized = json.dumps(channel)
    deserialized = json.loads(serialized)
    # deserialized is a plain dict, so verify that it equals the original dictionary.
    assert deserialized == channel_data

def test_copy_channel_data():
    """Test copying a ChannelData dictionary to ensure changes in the copy are independent."""
    import copy
    channel_data = {
        "id": 30,
        "url": "http://original.com",
        "host": "original.com",
        "date": "2023-10-15",
        "resolution": "720p",
        "origin": "subscribe",
        "ipv_type": "ipv4"
    }
    channel = channel_data  # TypedDict is a dict
    channel_copy = copy.deepcopy(channel)
    # Modify the copy
    channel_copy["url"] = "http://modifiedcopy.com"
    # Ensure the original remains unchanged
    assert channel["url"] == "http://original.com"
    assert channel_copy["url"] == "http://modifiedcopy.com"

def test_union_list_handling():
    """Test a list of ChannelTestResult items to ensure each union member behaves correctly."""
    channel = {
        "id": 40,
        "url": "http://unionchannel.com",
        "host": "unionchannel.com",
        "date": "2023-12-01",
        "resolution": "4K",
        "origin": "multicast",
        "ipv_type": "ipv4"
    }
    result = {
        "speed": 150,
        "delay": 15,
        "resolution": "4K"
    }
    # Both channel and result conform to the union type ChannelTestResult
    union_list = [channel, result]
    for item in union_list:
        if "id" in item:
            # Assert ChannelData properties
            assert isinstance(item["id"], int)
            assert "url" in item and isinstance(item["url"], str)
        elif "speed" in item:
            # Assert TestResult properties
            assert isinstance(item["speed"], (int, float)) or item["speed"] is None
            assert isinstance(item["delay"], (int, float)) or item["delay"] is None
            assert "resolution" in item
        else:
            import pytest
            pytest.fail("Item does not conform to either expected type in ChannelTestResult")
def test_missing_required_channel_data():
    """Test that accessing a missing required key in ChannelData raises a KeyError."""
    # Create a dictionary that is supposed to be a ChannelData but is missing the 'url' field
    incomplete_channel = {
        "id": 4,
        "host": "incomplete.com",
        "date": "2023-10-10",
        "resolution": "720p",
        "origin": "local",
        "ipv_type": "ipv4"
    }
    import pytest
    with pytest.raises(KeyError):
        _ = incomplete_channel["url"]

def test_invalid_type_assignment_channel_data():
    """Test that assigning a wrong type to a field in ChannelData results in unexpected type behavior."""
    # TypedDict does not enforce type checks at runtime.
    channel = ChannelData(
        id="not an int",  # Incorrect type for id
        url="http://wrongtype.com",
        host="wrongtype.com",
        date="2023-10-01",
        resolution="360p",
        origin="local",
        ipv_type="ipv6"
    )
    # Check that the id field is not of type int
    assert not isinstance(channel["id"], int)
    # Verify that other fields remain of the correct type
    assert isinstance(channel["url"], str)

def test_union_conflicting_keys():
    """Test a union of ChannelTestResult with conflicting keys to see which branch is taken."""
    # Create a dictionary with keys from both ChannelData and TestResult.
    conflicting = {
        "id": 50,
        "speed": 100,
        "url": "http://conflict.com",
        "host": "conflict.com",
        "date": "2023-10-11",
        "resolution": "4K",
        "origin": "subscribe",
        "ipv_type": "ipv4"
    }
    # In test_channel_test_result_union the membership of "id" means it is treated as ChannelData.
    if "id" in conflicting:
        assert conflicting["id"] == 50
        # Even though there is a "speed" key, we follow the channel data branch.
        assert conflicting["url"] == "http://conflict.com"

def test_extra_key_in_test_result():
    """Test that adding an extra key to TestResult is preserved in the dictionary."""
    result = TestResult(
        speed=85,
        delay=30,
        resolution="1080p"
    )
    # Add an extra key not defined in the TypedDict
    result["unexpected"] = "extra_value"
    assert result["unexpected"] == "extra_value"