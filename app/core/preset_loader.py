"""
Preset Loader
Loads device-specific test presets from YAML files
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class HardwareSpec(BaseModel):
    """Hardware specifications"""
    cpu: Optional[str] = None
    ram: Optional[str] = None
    storage: Optional[str] = None
    network: Optional[str] = None
    gpu: Optional[str] = None


class TestPreset(BaseModel):
    """Test preset configuration"""
    id: str = Field(..., description="Unique preset identifier")
    name: str = Field(..., description="Preset name")
    description: str = Field(..., description="Preset description")
    device_type: str = Field(..., description="Device type")
    manufacturer: str = Field(..., description="Manufacturer")
    model: str = Field(..., description="Device model")
    hardware: Optional[HardwareSpec] = None
    test_cases: List[str] = Field(default_factory=list, description="List of test case IDs")


class PresetLoader:
    """Loads test presets from YAML files"""
    
    def __init__(self, presets_dir: str = "presets"):
        self.presets_dir = Path(presets_dir)
        self.loaded_presets: Dict[str, TestPreset] = {}
        
    def load_all(self) -> List[TestPreset]:
        """Load all presets from YAML files"""
        logger.info(f"Loading presets from {self.presets_dir}")
        
        if not self.presets_dir.exists():
            logger.warning(f"Presets directory not found: {self.presets_dir}")
            return []
        
        presets = []
        
        # Find all YAML files
        for yaml_file in self.presets_dir.glob("*.yaml"):
            try:
                preset = self.load_from_file(yaml_file)
                if preset:
                    presets.append(preset)
                    self.loaded_presets[preset.id] = preset
                    logger.info(f"✓ Loaded preset: {preset.name} ({preset.id})")
            except Exception as e:
                logger.error(f"✗ Error loading preset {yaml_file.name}: {e}")
        
        logger.info(f"Total presets loaded: {len(presets)}")
        return presets
    
    def load_from_file(self, file_path: Path) -> Optional[TestPreset]:
        """Load preset from a single YAML file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'preset' not in data:
            logger.warning(f"No preset found in {file_path}")
            return None
        
        preset_data = data['preset']
        
        # Parse hardware spec if present
        hardware_spec = None
        if 'hardware' in preset_data:
            hardware_spec = HardwareSpec(**preset_data['hardware'])
        
        preset = TestPreset(
            id=preset_data['id'],
            name=preset_data['name'],
            description=preset_data.get('description', ''),
            device_type=preset_data.get('device_type', 'Unknown'),
            manufacturer=preset_data.get('manufacturer', 'Unknown'),
            model=preset_data.get('model', 'Unknown'),
            hardware=hardware_spec,
            test_cases=preset_data.get('test_cases', [])
        )
        
        return preset
    
    def get_by_id(self, preset_id: str) -> Optional[TestPreset]:
        """Get preset by ID"""
        return self.loaded_presets.get(preset_id)
    
    def get_by_model(self, model: str) -> List[TestPreset]:
        """Get presets by device model"""
        return [p for p in self.loaded_presets.values() if p.model.lower() == model.lower()]
    
    def get_by_manufacturer(self, manufacturer: str) -> List[TestPreset]:
        """Get presets by manufacturer"""
        return [p for p in self.loaded_presets.values() if p.manufacturer.lower() == manufacturer.lower()]

