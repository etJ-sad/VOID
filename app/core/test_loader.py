"""
Test Case Loader
Loads and validates test cases from YAML files
Supports hierarchical folder structure
"""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any
from app.models.schemas import TestCase

logger = logging.getLogger(__name__)


class TestCaseLoader:
    """Loads test cases from YAML files with hierarchical structure support"""
    
    def __init__(self, testcases_dir: str = "testcases"):
        self.testcases_dir = Path(testcases_dir)
        self.loaded_tests: Dict[str, TestCase] = {}
        
    def load_all(self) -> List[TestCase]:
        """Load all test cases from YAML files (recursive)"""
        logger.info(f"Loading test cases from {self.testcases_dir}")
        
        if not self.testcases_dir.exists():
            logger.warning(f"Test cases directory not found: {self.testcases_dir}")
            return []
        
        # Reset loaded_tests to avoid duplicates from previous loads
        self.loaded_tests = {}
        
        test_cases = []
        
        # Recursively find all YAML files
        for yaml_file in self.testcases_dir.rglob("*.yaml"):
            try:
                tests = self.load_from_file(yaml_file)
                test_cases.extend(tests)
                
                # Show relative path for better logging
                relative_path = yaml_file.relative_to(self.testcases_dir)
                logger.info(f"✓ Loaded {len(tests)} test(s) from {relative_path}")
            except Exception as e:
                logger.error(f"✗ Error loading {yaml_file.name}: {e}")
        
        # Log category summary
        categories = {}
        for test in test_cases:
            categories[test.category] = categories.get(test.category, 0) + 1
        
        logger.info(f"Total test cases loaded: {len(test_cases)}")
        for category, count in sorted(categories.items()):
            logger.info(f"  - {category}: {count} test(s)")
        
        return test_cases
    
    def load_from_file(self, file_path: Path) -> List[TestCase]:
        """Load test cases from a single YAML file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'tests' not in data:
            logger.warning(f"No tests found in {file_path}")
            return []
        
        test_cases = []
        
        for idx, test_data in enumerate(data['tests']):
            try:
                # Validate that ID exists in YAML - IDs should come from YAML file
                if 'id' not in test_data or not test_data['id'] or not str(test_data['id']).strip():
                    raise ValueError(
                        f"Test case #{idx+1} in {file_path} is missing required 'id' field. "
                        f"Each test case must have a unique ID defined in the YAML file."
                    )
                
                # Get ID from YAML - IDs must be defined in YAML file
                test_id = str(test_data['id']).strip()
                
                # Light normalization: only lowercase for consistency, keep original structure
                # This ensures case-insensitive uniqueness while preserving the original ID
                normalized_id_for_check = test_id.lower()
                
                # Validate ID format: should be alphanumeric with underscores/hyphens
                # Warn if it contains unusual characters, but don't reject it
                if not all(c.isalnum() or c in ['_', '-'] for c in test_id):
                    logger.warning(
                        f"Test ID '{test_id}' in {file_path} contains special characters. "
                        f"Recommended format: alphanumeric with underscores or hyphens (e.g., 'cpu_stress_test_1')"
                    )
                
                # Validate ID is unique (case-insensitive check)
                for existing_id, existing_test in self.loaded_tests.items():
                    if existing_id.lower() == normalized_id_for_check:
                        raise ValueError(
                            f"Duplicate test ID '{test_id}' found in {file_path}. "
                            f"ID '{test_id}' (case-insensitive match) is already used by test '{existing_test.name}'. "
                            f"Each test case must have a unique ID."
                        )
                
                # Keep original ID from YAML - don't normalize it
                # The ID should be exactly as written in the YAML file
                test_data['id'] = test_id
                
                test_case = TestCase(**test_data)
                
                # Final validation: ensure ID is set
                if not test_case.id or not test_case.id.strip():
                    raise ValueError(f"Test case ID is empty after processing in {file_path}")
                
                test_cases.append(test_case)
                self.loaded_tests[test_case.id] = test_case
                
                logger.debug(f"Loaded test case: ID={test_case.id}, Name={test_case.name}, Category={test_case.category}")
            except ValueError as e:
                # ValueError means missing or invalid ID - this is a critical error
                logger.error(f"Error parsing test case #{idx+1} in {file_path}: {e}")
                raise  # Re-raise to stop loading this file
            except Exception as e:
                logger.error(f"Error parsing test case #{idx+1} in {file_path}: {e}", exc_info=True)
        
        return test_cases
    
    def get_by_category(self, category: str) -> List[TestCase]:
        """Get all test cases for a specific category"""
        return [test for test in self.loaded_tests.values() 
                if test.category.lower() == category.lower()]
    
    def get_by_id(self, test_id: str) -> TestCase:
        """Get a test case by ID"""
        return self.loaded_tests.get(test_id)
    
    def save_test_case(self, test_case: TestCase, subfolder: str = None) -> Path:
        """Save a test case to YAML file"""
        # Determine file path based on category and test_type
        category_folder = self.testcases_dir / test_case.category.lower()
        if subfolder:
            category_folder = category_folder / subfolder
        elif test_case.test_type:
            category_folder = category_folder / test_case.test_type.lower()
        else:
            category_folder = category_folder / "custom"
        
        category_folder.mkdir(parents=True, exist_ok=True)
        
        # Generate filename from test ID
        filename = f"{test_case.id}.yaml"
        file_path = category_folder / filename
        
        # Create YAML structure
        yaml_data = {
            "tests": [
                {
                    "id": test_case.id,
                    "name": test_case.name,
                    "category": test_case.category,
                    "description": test_case.description,
                    "duration_estimate": test_case.duration_estimate,
                    "priority": test_case.priority,
                    "test_type": test_case.test_type,
                    "preconditions": test_case.preconditions,
                    "parameters": test_case.parameters,
                    "thresholds": test_case.thresholds,
                    "baseline": test_case.baseline
                }
            ]
        }
        
        # Write YAML file
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        logger.info(f"Saved test case {test_case.id} to {file_path}")
        
        # Reload to update cache
        self.loaded_tests[test_case.id] = test_case
        
        return file_path
    
    def delete_test_case(self, test_id: str) -> bool:
        """Delete a test case by finding and removing its YAML file"""
        # Find the file containing this test
        for yaml_file in self.testcases_dir.rglob("*.yaml"):
            try:
                tests = self.load_from_file(yaml_file)
                for test in tests:
                    if test.id == test_id:
                        # Found the file, delete it
                        yaml_file.unlink()
                        logger.info(f"Deleted test case {test_id} from {yaml_file}")
                        # Remove from cache
                        if test_id in self.loaded_tests:
                            del self.loaded_tests[test_id]
                        return True
            except Exception as e:
                logger.error(f"Error checking {yaml_file}: {e}")
        
        return False

