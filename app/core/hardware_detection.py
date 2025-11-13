"""
Hardware Detection Layer
Detects and enumerates all IPC hardware components
"""

import platform
import psutil
import uuid
from typing import Dict, List, Any
from datetime import datetime
from app.models.schemas import HardwareProfile, HardwareComponent
import logging

logger = logging.getLogger(__name__)


class HardwareDetector:
    """Detects all hardware components in the IPC"""
    
    def __init__(self):
        self.ipc_id = str(uuid.uuid4())
        
    def detect_all(self) -> HardwareProfile:
        """Detect all hardware components"""
        logger.info(f"Starting hardware detection for IPC: {self.ipc_id}")
        
        profile = HardwareProfile(
            ipc_id=self.ipc_id,
            ipc_model=self._detect_ipc_model(),
            cpu=self._detect_cpu(),
            ram=self._detect_ram(),
            gpu=self._detect_gpu(),
            storage=self._detect_storage(),
            network=self._detect_network(),
            sensors=self._detect_sensors()
        )
        
        logger.info(f"Hardware detection completed: {profile.ipc_model}")
        return profile
    
    def _detect_ipc_model(self) -> str:
        """Detect IPC model"""
        try:
            # Try to detect SIMATIC IPC models
            # Check environment variables first
            import os
            ipc_model = os.environ.get('SIMATIC_IPC_MODEL') or os.environ.get('IPC_MODEL')
            if ipc_model:
                return ipc_model
            
            # Try Windows-specific detection methods
            system = platform.system()
            if system == "Windows":
                # Try WMI to get system model
                try:
                    import wmi
                    c = wmi.WMI()
                    for system_info in c.Win32_ComputerSystem():
                        model = system_info.Model or ""
                        manufacturer = system_info.Manufacturer or ""
                        
                        # Check if it's a SIMATIC IPC
                        if 'simatic' in manufacturer.lower() or 'simatic' in model.lower():
                            # Extract specific model
                            model_lower = model.lower()
                            if 'rw-545a' in model_lower or 'rw545a' in model_lower:
                                return "SIMATIC IPC RW-545A"
                            elif 'bx-39a' in model_lower or 'bx39a' in model_lower:
                                return "SIMATIC IPC BX-39A"
                            elif 'bx-32a' in model_lower or 'bx32a' in model_lower:
                                return "SIMATIC IPC BX-32A"
                            elif 'rw' in model_lower:
                                return "SIMATIC IPC RW Series"
                            elif 'bx' in model_lower:
                                return "SIMATIC IPC BX Series"
                            else:
                                return f"SIMATIC IPC {model}"
                except ImportError:
                    logger.debug("WMI not available, trying alternative methods")
                except Exception as e:
                    logger.debug(f"WMI detection failed: {e}")
                
                # Try registry (Windows) - Primary method for Windows
                try:
                    import winreg
                    # Try to read from registry
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                            r"SYSTEM\CurrentControlSet\Control\SystemInformation")
                        model, _ = winreg.QueryValueEx(key, "SystemProductName")
                        manufacturer, _ = winreg.QueryValueEx(key, "SystemManufacturer")
                        winreg.CloseKey(key)
                        
                        logger.info(f"Registry detection: Manufacturer={manufacturer}, Model={model}")
                        
                        if model and manufacturer:
                            model_str = f"{manufacturer} {model}"
                            model_lower = model_str.lower()
                            
                            # Check for SIMATIC IPC
                            if 'simatic' in manufacturer.lower() or 'simatic' in model.lower():
                                # Extract specific model
                                if 'rw-545a' in model_lower or 'rw545a' in model_lower or 'rw 545a' in model_lower:
                                    return "SIMATIC IPC RW-545A"
                                elif 'bx-39a' in model_lower or 'bx39a' in model_lower or 'bx 39a' in model_lower:
                                    return "SIMATIC IPC BX-39A"
                                elif 'bx-32a' in model_lower or 'bx32a' in model_lower or 'bx 32a' in model_lower:
                                    return "SIMATIC IPC BX-32A"
                                elif 'rw' in model_lower:
                                    return "SIMATIC IPC RW Series"
                                elif 'bx' in model_lower:
                                    return "SIMATIC IPC BX Series"
                                else:
                                    # Return full model string if SIMATIC detected
                                    return model_str
                            # Also check if model contains RW-545A, BX-39A, etc. even without SIMATIC prefix
                            elif 'rw-545a' in model_lower or 'rw545a' in model_lower or 'rw 545a' in model_lower:
                                return "SIMATIC IPC RW-545A"
                            elif 'bx-39a' in model_lower or 'bx39a' in model_lower or 'bx 39a' in model_lower:
                                return "SIMATIC IPC BX-39A"
                            elif 'bx-32a' in model_lower or 'bx32a' in model_lower or 'bx 32a' in model_lower:
                                return "SIMATIC IPC BX-32A"
                    except FileNotFoundError:
                        logger.debug("Registry key not found")
                    except Exception as e:
                        logger.debug(f"Registry read error: {e}")
                except ImportError:
                    logger.debug("winreg not available")
                except Exception as e:
                    logger.debug(f"Registry detection failed: {e}")
            
            # Try to detect from system information
            machine = platform.machine()
            processor = platform.processor() or ""
            
            # Check for SIMATIC IPC indicators in processor/system info
            system_info = platform.platform().lower()
            processor_lower = processor.lower()
            
            # Pattern matching for SIMATIC IPC models
            if 'simatic' in system_info or 'simatic' in processor_lower:
                # Try to extract model number
                if 'rw-545a' in system_info or 'rw-545a' in processor_lower or 'rw545a' in system_info or 'rw545a' in processor_lower:
                    return "SIMATIC IPC RW-545A"
                elif 'bx-39a' in system_info or 'bx-39a' in processor_lower or 'bx39a' in system_info or 'bx39a' in processor_lower:
                    return "SIMATIC IPC BX-39A"
                elif 'bx-32a' in system_info or 'bx-32a' in processor_lower or 'bx32a' in system_info or 'bx32a' in processor_lower:
                    return "SIMATIC IPC BX-32A"
                elif 'rw' in system_info or 'rw' in processor_lower:
                    return "SIMATIC IPC RW Series"
                elif 'bx' in system_info or 'bx' in processor_lower:
                    return "SIMATIC IPC BX Series"
                else:
                    return "SIMATIC IPC"
            
            # Fallback to generic system info
            return f"{system} {machine}"
        except Exception as e:
            logger.error(f"Error detecting IPC model: {e}")
            return "Unknown IPC"
    
    def get_current_ipc_model(self) -> str:
        """Get current IPC model (cached)"""
        if not hasattr(self, '_cached_model'):
            self._cached_model = self._detect_ipc_model()
            logger.info(f"Detected IPC model: {self._cached_model}")
        return self._cached_model
    
    def _detect_cpu(self) -> HardwareComponent:
        """Detect CPU information"""
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "max_frequency_mhz": cpu_freq.max if cpu_freq else 0,
                "current_frequency_mhz": cpu_freq.current if cpu_freq else 0,
                "architecture": platform.machine(),
                "processor": platform.processor()
            }
            
            return HardwareComponent(
                component_type="CPU",
                name=platform.processor() or "Unknown CPU",
                details=cpu_info
            )
        except Exception as e:
            logger.error(f"Error detecting CPU: {e}")
            return HardwareComponent(
                component_type="CPU",
                name="Unknown CPU",
                details={"error": str(e)}
            )
    
    def _detect_ram(self) -> List[HardwareComponent]:
        """Detect RAM information"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            ram_component = HardwareComponent(
                component_type="RAM",
                name=f"{memory.total // (1024**3)}GB RAM",
                details={
                    "total_bytes": memory.total,
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent,
                    "swap_total_gb": round(swap.total / (1024**3), 2) if swap.total > 0 else 0
                }
            )
            
            return [ram_component]
        except Exception as e:
            logger.error(f"Error detecting RAM: {e}")
            return []
    
    def _detect_gpu(self) -> List[HardwareComponent]:
        """Detect GPU information"""
        gpus = []
        
        try:
            # Try to detect NVIDIA GPU using nvidia-smi
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(',')
                        name = parts[0].strip()
                        memory = parts[1].strip() if len(parts) > 1 else "Unknown"
                        
                        gpus.append(HardwareComponent(
                            component_type="GPU",
                            name=name,
                            details={"memory": memory, "vendor": "NVIDIA"}
                        ))
        except Exception as e:
            logger.debug(f"NVIDIA GPU detection failed: {e}")
        
        # If no GPU detected, add a placeholder
        if not gpus:
            gpus.append(HardwareComponent(
                component_type="GPU",
                name="Integrated Graphics",
                details={"vendor": "Unknown", "note": "No discrete GPU detected"}
            ))
        
        return gpus
    
    def _detect_storage(self) -> List[HardwareComponent]:
        """Detect storage devices"""
        storage_devices = []
        
        try:
            partitions = psutil.disk_partitions()
            seen_devices = set()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    device_key = partition.device
                    
                    if device_key not in seen_devices:
                        seen_devices.add(device_key)
                        
                        storage_devices.append(HardwareComponent(
                            component_type="Storage",
                            name=f"{partition.device} ({usage.total // (1024**3)}GB)",
                            details={
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "fstype": partition.fstype,
                                "total_gb": round(usage.total / (1024**3), 2),
                                "used_gb": round(usage.used / (1024**3), 2),
                                "free_gb": round(usage.free / (1024**3), 2),
                                "percent_used": usage.percent
                            }
                        ))
                except Exception as e:
                    logger.debug(f"Error reading partition {partition.device}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error detecting storage: {e}")
        
        return storage_devices
    
    def _detect_network(self) -> List[HardwareComponent]:
        """Detect network interfaces"""
        network_interfaces = []
        
        try:
            if_addrs = psutil.net_if_addrs()
            if_stats = psutil.net_if_stats()
            
            for interface_name, addresses in if_addrs.items():
                if interface_name == 'lo' or interface_name.startswith('lo'):
                    continue  # Skip loopback
                
                stats = if_stats.get(interface_name)
                
                details = {
                    "interface": interface_name,
                    "is_up": stats.isup if stats else False,
                    "speed_mbps": stats.speed if stats else 0,
                    "addresses": []
                }
                
                for addr in addresses:
                    details["addresses"].append({
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask
                    })
                
                network_interfaces.append(HardwareComponent(
                    component_type="Network",
                    name=interface_name,
                    details=details
                ))
        except Exception as e:
            logger.error(f"Error detecting network: {e}")
        
        return network_interfaces
    
    def _detect_sensors(self) -> List[HardwareComponent]:
        """Detect hardware sensors (temperature, fans, etc.)"""
        sensors = []
        
        try:
            # Try to get temperature sensors
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if temps:
                    for sensor_name, entries in temps.items():
                        for entry in entries:
                            sensors.append(HardwareComponent(
                                component_type="Sensor",
                                name=f"Temperature: {entry.label or sensor_name}",
                                details={
                                    "sensor_type": "temperature",
                                    "current_celsius": entry.current,
                                    "high_celsius": entry.high if entry.high else None,
                                    "critical_celsius": entry.critical if entry.critical else None
                                }
                            ))
        except Exception as e:
            logger.debug(f"Temperature sensor detection failed: {e}")
        
        try:
            # Try to get fan sensors
            if hasattr(psutil, 'sensors_fans'):
                fans = psutil.sensors_fans()
                if fans:
                    for fan_name, entries in fans.items():
                        for entry in entries:
                            sensors.append(HardwareComponent(
                                component_type="Sensor",
                                name=f"Fan: {entry.label or fan_name}",
                                details={
                                    "sensor_type": "fan",
                                    "current_rpm": entry.current
                                }
                            ))
        except Exception as e:
            logger.debug(f"Fan sensor detection failed: {e}")
        
        # If no sensors detected, add CPU usage as a "sensor"
        if not sensors:
            sensors.append(HardwareComponent(
                component_type="Sensor",
                name="CPU Usage Monitor",
                details={
                    "sensor_type": "cpu_percent",
                    "current_percent": psutil.cpu_percent(interval=1)
                }
            ))
        
        return sensors

