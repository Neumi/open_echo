from enum import StrEnum
from pydantic import BaseModel, Field, field_validator


class Medium(StrEnum):
    WATER = "water"
    AIR = "air"


class NMEAOffset(StrEnum):
    ToKeel = "to_keel"
    ToSurface = "to_surface"
    ToTransducer = "to_transducer"


speed_of_sound_map = {
    Medium.WATER: 1480,  # meters per second in water
    Medium.AIR: 330,  # meters per second in air
}


class Settings(BaseModel):
    serial_port: str = "init"
    baud_rate: int = 250000
    num_samples: int = 1800
    blindzone_sample_end: int = 150
    threshold_value: int = 25
    colormap: str = "viridis"
    transducer_depth: float = Field(default=0.0, ge=0)
    draft: float = Field(default=0.0, ge=0)
    depth_output_enable: bool = False
    medium: Medium = Medium.WATER
    dynamic_resolution: bool = False
    signalk_enable: bool = False
    signalk_address: str = "localhost:3000"
    nmea_enable: bool = False
    nmea_address: str = "localhost:10110"
    nmea_offset: NMEAOffset | None = None
    override_detected_depth: bool = False
    signalk_token: str | None = None
    depth_detection_threshold: float = Field(default=2.0, ge=0)

    @field_validator("colormap")
    def validate_colormap(cls, v):
        allowed = {"viridis", "plasma", "inferno", "magma", "terrain"}
        if v not in allowed:
            raise ValueError(f"Colormap must be one of {allowed}")
        return v

    @property
    def resolution(self):
        """Calculate resolution based on medium and dynamic resolution setting."""
        if self.medium not in speed_of_sound_map:
            raise ValueError(f"Unsupported medium: {self.medium}")

        speed_of_sound = speed_of_sound_map[self.medium]
        return speed_of_sound * 13.2e-6 * 100 / 2  # cm per row (0.99 cm per row)

    @property
    def output_methods(self):
        methods = []
        if self.signalk_enable:
            methods.append("signalk")
        if self.nmea_enable:
            methods.append("nmea0183")
        return methods

    def save(self, filename=".settings.json"):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, filename=".settings.json"):
        with open(filename, "r", encoding="utf-8") as f:
            data = f.read()
        
        return cls.model_validate_json(data)