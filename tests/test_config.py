import os
import sys
import io
import shutil
import configparser
import pytest

from utils.config import resource_path, get_resolution_value, ConfigManager, config


def test_get_resolution_value():
    """Test resolution value computation with various valid and invalid strings."""
    # valid cases: using "x", "X", and "*" as separator
    assert get_resolution_value("1920x1080") == 1920 * 1080
    assert get_resolution_value("800X600") == 800 * 600
    assert get_resolution_value("1024*768") == 1024 * 768

    # invalid case
    assert get_resolution_value("no_resolution") == 0


def test_resource_path_exists(monkeypatch, tmp_path):
    """Test resource_path when the file exists or persistent flag is set."""
    # Create a temporary dummy file
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("data")
    # Simulate the current directory being tmp_path
    monkeypatch.chdir(tmp_path)

    # When file exists and persistent is False, should return the path
    rel_path = "dummy.txt"
    path1 = resource_path(rel_path, persistent=False)
    assert os.path.exists(path1)

    # Force persistent True even if file not exists: (here we test that persistent=True returns same joined path)
    rel_path_nonexistent = "nonexistent.txt"
    path2 = resource_path(rel_path_nonexistent, persistent=True)
    expected = os.path.join(os.path.abspath("."), rel_path_nonexistent)
    assert path2 == expected

def test_resource_path_sys_meipass(monkeypatch, tmp_path):
    """Test resource_path when file does not exist and sys._MEIPASS is set."""
    # Ensure that os.path.exists returns False for our test file.
    fake_exists = lambda x: False
    monkeypatch.setattr(os.path, "exists", fake_exists)

    # Set fake sys._MEIPASS value
    fake_meipass = str(tmp_path / "meipass")
    monkeypatch.setitem(sys.__dict__, "_MEIPASS", fake_meipass)

    rel_path = "dummy.txt"
    result = resource_path(rel_path, persistent=False)
    expected = os.path.join(fake_meipass, rel_path)
    assert result == expected


class DummyFile(io.StringIO):
    """A dummy file object to record written content."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = ""

    def write(self, s):
        self.content += s
        return super().write(s)


@pytest.fixture
def fake_config_files(monkeypatch):
    """
    Fixture to simulate configuration file contents.
    The default config file and the user config file are simulated.
    """
    default_config_content = (
        "[Settings]\n"
        "open_service = false\n"
        "ipv_type = ipv4\n"
        "urls_limit = 20\n"
        "min_resolution = 1280x720\n"
    )
    user_config_content = (
        "[Settings]\n"
        "open_service = true\n"
        "ipv_type = 全部\n"
        "urls_limit = 50\n"
    )

    def fake_open(file, mode="r", encoding=None):
        if "user_config.ini" in file:
            return io.StringIO(user_config_content)
        elif "config.ini" in file:
            return io.StringIO(default_config_content)
        else:
            raise FileNotFoundError(f"File {file} not found in fake_open")

    monkeypatch.setattr("builtins.open", fake_open)

    # Make os.path.exists return True when checking for these simulated files
    def fake_exists(path):
        if "config/config.ini" in path or "config/user_config.ini" in path:
            return True
        return False

    monkeypatch.setattr(os.path, "exists", fake_exists)

@pytest.fixture
def config_manager(fake_config_files):
    """Return a new ConfigManager instance that loads from the fake config files."""
    cm = ConfigManager()
    return cm


def test_config_properties(config_manager, monkeypatch):
    """Test that ConfigManager properties reflect the fake configuration files (user config overwrites default)."""
    # open_service should be True as set by user_config.ini overriding default false.
    assert config_manager.open_service is True

    # ipv_type from user_config should be "全部" (and lowercased) 
    assert config_manager.ipv_type == "全部"

    # urls_limit should come from user_config i.e., 50.
    assert config_manager.urls_limit == 50

    # min_resolution is not overridden so should come from default config: "1280x720"
    assert config_manager.min_resolution == "1280x720"

    # Verify min_resolution_value calculation: 1280*720
    assert config_manager.min_resolution_value == 1280 * 720


def test_config_set_and_save(monkeypatch, tmp_path, fake_config_files):
    """Test that setting a new value and saving writes out the configuration."""
    # Use a real temporary file by patching resource_path to use tmp_path for user_config.ini.
    def fake_resource_path(relative_path, persistent=False):
        return os.path.join(str(tmp_path), relative_path)

    monkeypatch.setattr("utils.config.resource_path", fake_resource_path)

    cm = ConfigManager()
    # Set a new value in the config
    cm.set("Settings", "test_key", "test_value")

    # Prepare a dummy file object to capture what is written
    dummy_file = DummyFile()
    def fake_open_write(file, mode="w", encoding=None):
        return dummy_file

    monkeypatch.setattr("builtins.open", fake_open_write)

    # Also patch os.makedirs to do nothing
    monkeypatch.setattr(os, "makedirs", lambda d, exist_ok=True: None)

    cm.save()
    # Check that the dummy file has the test key
    assert "test_key" in dummy_file.content


def test_copy(monkeypatch, tmp_path):
    """Test the copy method by faking a source config directory with one file."""
    # Create a fake source directory with one file inside it.
    src_config_dir = tmp_path / "src_config"
    src_config_dir.mkdir()
    dummy_file_path = src_config_dir / "dummy.txt"
    dummy_file_path.write_text("dummy data")

    # Set up fake resource_path to return our src_config_dir when "config" is requested.
    def fake_resource_path(relative_path, persistent=False):
        if relative_path == "config":
            return str(src_config_dir)
        return os.path.join(str(tmp_path), relative_path)

    monkeyatch_resource_path = fake_resource_path
    monkeypatch.setattr("utils.config.resource_path", monkeyatch_resource_path)

    # Patch os.getcwd to return a temporary destination directory.
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()
    monkeypatch.setattr(os, "getcwd", lambda: str(dest_dir))

    cm = ConfigManager()
    cm.copy()

    # The destination folder should be dest_dir/config with file dummy.txt copied.
    copied_file = dest_dir / "config" / "dummy.txt"
    assert copied_file.exists()
    assert copied_file.read_text() == "dummy data"


def test_app_port_override(monkeypatch, fake_config_files):
    """Test that the app_port property correctly reads from the APP_PORT environment variable."""
    test_port = "12345"
    monkeypatch.setenv("APP_PORT", test_port)

    cm = ConfigManager()
    # Since APP_PORT is an env var, the property should return that value (as a str or int)
    assert str(cm.app_port) == test_port


def test_open_driver(monkeypatch, fake_config_files):
    """Test that open_driver reflects the LITE environment variable (if set, open_driver returns False)."""
    # First, without LITE set. Assume default from config is True.
    if "LITE" in os.environ:
        monkeyatch_del = monkeypatch.delenv("LITE", raising=False)
    cm = ConfigManager()
    assert cm.open_driver is True

    # Now, set LITE in the environment, should force open_driver to be False.
    monkeypatch.setenv("LITE", "1")
    cm2 = ConfigManager()
    assert cm2.open_driver is False


def test_ipv_properties(fake_config_files):
    """Test ipv related properties even if using default fallbacks."""
    cm = ConfigManager()
    # By default, if ipv_type is not overridden in user config, it's set to "全部" from our fake config.
    # open_ipv6 returns True if ipv_type contains "ipv6" or "全部" or "all"
    assert cm.open_ipv6 is True

    # ipv_type_prefer: by default empty string fallback splits to empty list.
    assert isinstance(cm.ipv_type_prefer, list)
    assert len(cm.ipv_type_prefer) == 0

    # ipv4_num and ipv6_num: should return integer values, falling back to default (5)
    try:
        int(cm.ipv4_num)
        int(cm.ipv6_num)
    except Exception:
        pytest.fail("ipv4_num or ipv6_num not returning proper integer values")


def test_open_methods(fake_config_files):
    """Test the open_method property structure and edge cases."""
    cm = ConfigManager()
    # open_local is a property that uses fallback True.
    open_methods = cm.open_method
    # Check that keys for various methods are present.
    expected_keys = {"local", "subscribe", "hotel", "multicast", "online_search",
                        "hotel_fofa", "hotel_foodie", "multicast_fofa", "multicast_foodie"}
    assert expected_keys.issubset(open_methods.keys())
    # Their values should be boolean.
    for value in open_methods.values():
        assert isinstance(value, bool)

def test_online_search_page_num_property(fake_config_files):
    """Test that online_search_page_num returns the fallback value (1) when not provided in the config."""
    cm = ConfigManager()
    # online_search_page_num in ConfigManager calls config.getint using the module-level config and should return fallback 1
    assert cm.online_search_page_num == 1

def test_extra_properties(fake_config_files):
    """Test extra fallback properties like update_time_position, time_zone, cdn_url, and open_rtmp."""
    cm = ConfigManager()
    # update_time_position fallback is "top"
    assert cm.update_time_position == "top"
    # time_zone fallback is "Asia/Shanghai"
    assert cm.time_zone == "Asia/Shanghai"
    # cdn_url fallback is empty string
    assert cm.cdn_url == ""
    # open_rtmp fallback is False
    assert cm.open_rtmp is False

def test_getattr_forward(fake_config_files):
    """Test that __getattr__ forwards attribute requests to the underlying config object."""
    cm = ConfigManager()
    # Set a dummy attribute on the internal config 
    cm.config.some_dummy_attr = "dummy_value"
    assert cm.some_dummy_attr == "dummy_value"

def test_copy_error(monkeypatch, capsys):
    """Test that copy() properly prints an error message when an exception occurs."""
    # Force resource_path to return a path that will cause error in os.walk by returning a non-directory string.
    def fake_resource_path(relative_path, persistent=False):
        return "non_existent_directory"
    monkeypatch.setattr("utils.config.resource_path", fake_resource_path)
    # Patch os.path.exists so that our fake directory is seen as existing
    orig_exists = os.path.exists
    monkeypatch.setattr(os.path, "exists", lambda path: True if "non_existent_directory" in path else orig_exists(path))
    import builtins
    orig_open = builtins.open
    def fake_open(file, mode="r", encoding=None):
        if mode == "r":
            # Return a minimal dummy config so that load() succeeds.
            return io.StringIO("[Settings]\n")
        else:
            return orig_open(file, mode, encoding=encoding)
    monkeypatch.setattr("builtins.open", fake_open)
    # Patch os.walk to immediately raise an exception to simulate an error during file copy
    def fake_os_walk(path):
        raise Exception("Simulated error in os.walk")
    monkeypatch.setattr(os, "walk", fake_os_walk)

    cm = ConfigManager()
    # This will exercise the exception block in copy()
    cm.copy()
    captured = capsys.readouterr().out
    assert "Failed to copy files" in captured
    
# End of added tests
def test_config_empty_config(monkeypatch):
    """Test ConfigManager fallback values when no config files exist."""
    # Force os.path.exists to always return False so no config files are loaded
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    # Ensure the environment is clean for this test
    monkeypatch.delenv("APP_PORT", raising=False)
    monkeypatch.delenv("LITE", raising=False)
    cm = ConfigManager()
    # Fallback properties as defined in the ConfigManager
    assert cm.open_service is True
    assert cm.open_update is True
    assert cm.open_use_cache is True
    assert cm.open_request is False
    # Fallback value for ipv_type is "全部" then lowercased (although lower on Chinese characters remains unchanged)
    assert cm.ipv_type == "全部".lower()
    assert cm.ipv4_num == 5
    assert cm.ipv6_num == 5
    assert cm.ipv6_support is False
    # The fallback for min_resolution is "1920x1080"
    assert cm.min_resolution == "1920x1080"
    # Since APP_PORT is not set, the fallback app_port is 8000
    assert cm.app_port == 8000
    # Fallback for cdn_url is an empty string
    assert cm.cdn_url == ""

def test_config_fallback_properties(monkeypatch):
    """Test several fallback properties when config file is empty."""
    # Force an empty config by making os.path.exists always return False
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    cm = ConfigManager()
    # Check various numeric and boolean fallback properties
    assert cm.open_filter_speed is True
    assert cm.open_filter_resolution is True
    assert cm.hotel_num == 10
    assert cm.multicast_num == 10
    assert cm.subscribe_num == 10
    assert cm.online_search_num == 10
    assert cm.sort_timeout == 10
    assert cm.request_timeout == 10
    assert cm.open_proxy is False
    assert cm.hotel_page_num == 1
    assert cm.multicast_page_num == 1
    assert cm.online_search_page_num == 1
    assert cm.open_empty_category is True

def test_origin_type_prefer_and_multicast_region_list(monkeypatch):
    """Test fallback behavior for origin_type_prefer and region list properties."""
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    cm = ConfigManager()
    # origin_type_prefer fallback is an empty list when the string is empty
    assert cm.origin_type_prefer == []
    # multicast_region_list fallback should yield a list containing "全部"
    assert cm.multicast_region_list == ["全部"]
    # hotel_region_list fallback should yield a list containing "全部"
    assert cm.hotel_region_list == ["全部"]

def test_open_driver_default(monkeypatch):
    # Force no config files to be loaded by always returning False for os.path.exists
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    """Test that open_driver returns the fallback True if LITE is not set."""
    monkeypatch.delenv("LITE", raising=False)
    cm = ConfigManager()
    assert cm.open_driver is True

def test_open_driver_with_lite(monkeypatch):
    """Test that open_driver returns False when the LITE environment variable is set."""
    monkeypatch.setenv("LITE", "1")
    cm = ConfigManager()
    assert cm.open_driver is False

# End of new tests