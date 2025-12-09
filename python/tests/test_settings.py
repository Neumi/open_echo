import json
import math
import pytest

from openecho.settings import Settings, Medium, NMEAOffset
from openecho.echo import ConnectionTypeEnum


def test_connection_type_parsing_from_enum():
    s = Settings(connection_type=ConnectionTypeEnum.UDP)
    assert s.connection_type is ConnectionTypeEnum.UDP


def test_connection_type_parsing_from_string_name_case_insensitive():
    s = Settings(connection_type="serial")
    assert s.connection_type is ConnectionTypeEnum.SERIAL
    s2 = Settings(connection_type="UDP")
    assert s2.connection_type is ConnectionTypeEnum.UDP


def test_connection_type_parsing_invalid_string_raises():
    with pytest.raises(ValueError):
        Settings(connection_type="bluetooth")


def test_colormap_validation_accepts_allowed_values():
    for cmap in ["viridis", "plasma", "inferno", "magma", "terrain"]:
        s = Settings(colormap=cmap)
        assert s.colormap == cmap


def test_colormap_validation_rejects_unknown_value():
    with pytest.raises(ValueError):
        Settings(colormap="rainbow")


def test_resolution_water_and_air_calculation():
    # Expected resolution = speed_of_sound * 13.2e-6 * 100 / 2
    s_water = Settings(medium=Medium.WATER)
    s_air = Settings(medium=Medium.AIR)
    expected_water = 1480 * 13.2e-6 * 100 / 2
    expected_air = 330 * 13.2e-6 * 100 / 2
    assert math.isclose(s_water.resolution, expected_water, rel_tol=1e-9)
    assert math.isclose(s_air.resolution, expected_air, rel_tol=1e-9)


def test_resolution_unsupported_medium_raises():
    class FakeMedium(str):
        pass
    fake = FakeMedium("ice")
    # Bypass Pydantic constraint by setting after init
    s = Settings()
    s.medium = fake  # type: ignore[assignment]
    with pytest.raises(ValueError):
        _ = s.resolution


def test_output_methods_flags():
    s = Settings(signalk_enable=False, nmea_enable=False)
    assert s.output_methods == []
    s.signalk_enable = True
    assert s.output_methods == ["signalk"]
    s.nmea_enable = True
    assert set(s.output_methods) == {"signalk", "nmea0183"}


def test_save_and_load_roundtrip(tmp_path):
    s = Settings(
        connection_type=ConnectionTypeEnum.SERIAL,
        udp_port=8888,
        serial_port="/dev/tty.usbserial",
        baud_rate=115200,
        num_samples=1024,
        colormap="plasma",
        transducer_depth=1.2,
        draft=0.3,
        depth_output_enable=True,
        medium=Medium.WATER,
        signalk_enable=True,
        signalk_address="localhost:3000",
        nmea_enable=True,
        nmea_address="localhost:10110",
        nmea_offset=NMEAOffset.ToKeel,
        signalk_token="abc123",
    )

    file_path = tmp_path / "settings.json"
    s.save(str(file_path))

    # Ensure file content is valid JSON
    data = json.loads(file_path.read_text())
    assert data["connection_type"] == "SERIAL"

    s2 = Settings.load(str(file_path))
    assert s2 == s
    assert s2.connection_type is ConnectionTypeEnum.SERIAL
