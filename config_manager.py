
import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_folder: str):
        self.config_folder = config_folder
        self.presets_file = os.path.join(config_folder, 'presets.json')
        self.user_settings_file = os.path.join(config_folder, 'user_settings.json')
        
        # Ensure config folder exists
        os.makedirs(config_folder, exist_ok=True)
        
        # Initialize default presets
        self._initialize_default_presets()
        
    def _initialize_default_presets(self):
        """Initialize default configuration presets"""
        default_presets = {
            'high_quality': {
                'name': 'High Quality',
                'description': 'Best quality output with higher processing time',
                'settings': {
                    'fps': 25.0,
                    'resize_factor': 1,
                    'face_det_batch_size': 4,
                    'wav2lip_batch_size': 32,
                    'img_size': 96,
                    'pads': [0, 10, 0, 0],
                    'nosmooth': False,
                    'static': False,
                    'rotate': False
                }
            },
            'fast_processing': {
                'name': 'Fast Processing',
                'description': 'Faster processing with good quality',
                'settings': {
                    'fps': 25.0,
                    'resize_factor': 2,
                    'face_det_batch_size': 8,
                    'wav2lip_batch_size': 64,
                    'img_size': 96,
                    'pads': [0, 10, 0, 0],
                    'nosmooth': False,
                    'static': False,
                    'rotate': False
                }
            },
            'mobile_optimized': {
                'name': 'Mobile Optimized',
                'description': 'Optimized for mobile devices and smaller files',
                'settings': {
                    'fps': 24.0,
                    'resize_factor': 2,
                    'face_det_batch_size': 16,
                    'wav2lip_batch_size': 128,
                    'img_size': 96,
                    'pads': [0, 15, 0, 0],
                    'nosmooth': False,
                    'static': False,
                    'rotate': False
                }
            },
            'portrait_mode': {
                'name': 'Portrait Mode',
                'description': 'Optimized for portrait/vertical videos',
                'settings': {
                    'fps': 30.0,
                    'resize_factor': 1,
                    'face_det_batch_size': 6,
                    'wav2lip_batch_size': 48,
                    'img_size': 96,
                    'pads': [0, 20, 0, 0],
                    'nosmooth': False,
                    'static': False,
                    'rotate': False
                }
            },
            'batch_processing': {
                'name': 'Batch Processing',
                'description': 'Optimized for processing multiple files',
                'settings': {
                    'fps': 25.0,
                    'resize_factor': 2,
                    'face_det_batch_size': 16,
                    'wav2lip_batch_size': 128,
                    'img_size': 96,
                    'pads': [0, 10, 0, 0],
                    'nosmooth': True,
                    'static': False,
                    'rotate': False
                }
            }
        }
        
        # Load existing presets or create default ones
        if not os.path.exists(self.presets_file):
            self.save_presets(default_presets)
    
    def get_presets(self) -> Dict[str, Dict]:
        """Get all available presets"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading presets: {e}")
            return {}
    
    def save_presets(self, presets: Dict[str, Dict]):
        """Save presets to file"""
        try:
            with open(self.presets_file, 'w') as f:
                json.dump(presets, f, indent=2)
            logger.info("Presets saved successfully")
        except Exception as e:
            logger.error(f"Error saving presets: {e}")
    
    def get_preset(self, preset_id: str) -> Optional[Dict]:
        """Get a specific preset by ID"""
        presets = self.get_presets()
        return presets.get(preset_id)
    
    def create_preset(self, name: str, description: str, settings: Dict) -> str:
        """Create a new preset"""
        preset_id = str(uuid.uuid4())
        presets = self.get_presets()
        
        presets[preset_id] = {
            'name': name,
            'description': description,
            'settings': settings,
            'created_at': datetime.now().isoformat(),
            'custom': True
        }
        
        self.save_presets(presets)
        logger.info(f"Created new preset: {name}")
        return preset_id
    
    def update_preset(self, preset_id: str, name: str = None, 
                     description: str = None, settings: Dict = None) -> bool:
        """Update an existing preset"""
        presets = self.get_presets()
        
        if preset_id not in presets:
            return False
        
        if name is not None:
            presets[preset_id]['name'] = name
        if description is not None:
            presets[preset_id]['description'] = description
        if settings is not None:
            presets[preset_id]['settings'] = settings
        
        presets[preset_id]['updated_at'] = datetime.now().isoformat()
        
        self.save_presets(presets)
        logger.info(f"Updated preset: {preset_id}")
        return True
    
    def delete_preset(self, preset_id: str) -> bool:
        """Delete a preset (only custom presets)"""
        presets = self.get_presets()
        
        if preset_id not in presets:
            return False
        
        # Don't allow deletion of default presets
        if not presets[preset_id].get('custom', False):
            return False
        
        del presets[preset_id]
        self.save_presets(presets)
        logger.info(f"Deleted preset: {preset_id}")
        return True
    
    def get_user_settings(self) -> Dict:
        """Get user-specific settings"""
        try:
            if os.path.exists(self.user_settings_file):
                with open(self.user_settings_file, 'r') as f:
                    return json.load(f)
            return self._get_default_user_settings()
        except Exception as e:
            logger.error(f"Error loading user settings: {e}")
            return self._get_default_user_settings()
    
    def save_user_settings(self, settings: Dict):
        """Save user-specific settings"""
        try:
            with open(self.user_settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            logger.info("User settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving user settings: {e}")
    
    def _get_default_user_settings(self) -> Dict:
        """Get default user settings"""
        return {
            'theme': 'dark',
            'default_preset': 'high_quality',
            'auto_preview': True,
            'max_file_size_mb': 100,
            'auto_cleanup_hours': 24,
            'notification_settings': {
                'job_completion': True,
                'job_failure': True,
                'bulk_completion': True
            },
            'advanced_mode': False,
            'last_used_model': None
        }
    
    def get_micro_change_templates(self) -> Dict:
        """Get templates for micro-changes"""
        return {
            'lip_sync_strength': {
                'name': 'Lip Sync Strength',
                'description': 'Adjust the strength of lip synchronization',
                'parameter': 'wav2lip_batch_size',
                'min_value': 16,
                'max_value': 128,
                'default_value': 64,
                'step': 16,
                'impact': 'Higher values = stronger sync, longer processing'
            },
            'face_detection_sensitivity': {
                'name': 'Face Detection Sensitivity',
                'description': 'Adjust face detection batch size',
                'parameter': 'face_det_batch_size',
                'min_value': 2,
                'max_value': 32,
                'default_value': 8,
                'step': 2,
                'impact': 'Lower values = more sensitive detection'
            },
            'output_quality': {
                'name': 'Output Quality',
                'description': 'Adjust output resolution factor',
                'parameter': 'resize_factor',
                'min_value': 1,
                'max_value': 4,
                'default_value': 1,
                'step': 1,
                'impact': 'Higher values = lower resolution, faster processing'
            },
            'frame_rate': {
                'name': 'Frame Rate',
                'description': 'Adjust output frame rate',
                'parameter': 'fps',
                'min_value': 15.0,
                'max_value': 60.0,
                'default_value': 25.0,
                'step': 1.0,
                'impact': 'Higher FPS = smoother video, larger file size'
            },
            'face_padding': {
                'name': 'Face Padding',
                'description': 'Adjust padding around detected face',
                'parameter': 'pads',
                'min_value': [0, 5, 0, 0],
                'max_value': [10, 30, 10, 10],
                'default_value': [0, 10, 0, 0],
                'step': [1, 1, 1, 1],
                'impact': 'More padding = more context, may include unwanted areas'
            }
        }
    
    def apply_micro_changes(self, base_settings: Dict, micro_changes: Dict) -> Dict:
        """Apply micro-changes to base settings"""
        result_settings = base_settings.copy()
        templates = self.get_micro_change_templates()
        
        for change_id, value in micro_changes.items():
            if change_id in templates:
                template = templates[change_id]
                parameter = template['parameter']
                
                # Validate value range
                min_val = template['min_value']
                max_val = template['max_value']
                
                if isinstance(value, list):
                    # Handle list parameters (like pads)
                    validated_value = []
                    for i, v in enumerate(value):
                        if i < len(min_val) and i < len(max_val):
                            validated_value.append(max(min_val[i], min(max_val[i], v)))
                        else:
                            validated_value.append(v)
                    result_settings[parameter] = validated_value
                else:
                    # Handle scalar parameters
                    validated_value = max(min_val, min(max_val, value))
                    result_settings[parameter] = validated_value
        
        return result_settings
    
    def export_config(self, config_type: str = 'all') -> Dict:
        """Export configuration data"""
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        if config_type in ['all', 'presets']:
            export_data['presets'] = self.get_presets()
        
        if config_type in ['all', 'user_settings']:
            export_data['user_settings'] = self.get_user_settings()
        
        return export_data
    
    def import_config(self, config_data: Dict, overwrite: bool = False) -> bool:
        """Import configuration data"""
        try:
            if 'presets' in config_data:
                if overwrite:
                    self.save_presets(config_data['presets'])
                else:
                    # Merge with existing presets
                    existing_presets = self.get_presets()
                    for preset_id, preset_data in config_data['presets'].items():
                        if preset_id not in existing_presets:
                            existing_presets[preset_id] = preset_data
                    self.save_presets(existing_presets)
            
            if 'user_settings' in config_data:
                if overwrite:
                    self.save_user_settings(config_data['user_settings'])
                else:
                    # Merge with existing settings
                    existing_settings = self.get_user_settings()
                    existing_settings.update(config_data['user_settings'])
                    self.save_user_settings(existing_settings)
            
            logger.info("Configuration imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False

# Global config manager instance
config_manager = None

def get_config_manager(config_folder: str) -> ConfigManager:
    """Get or create the global config manager instance"""
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager(config_folder)
    return config_manager
