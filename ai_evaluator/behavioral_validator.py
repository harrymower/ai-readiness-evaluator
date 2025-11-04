"""Behavioral validation framework - validates CLI against behavioral requirements."""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import yaml


class BehavioralValidator:
    """Validates a CLI tool against behavioral requirements."""
    
    def __init__(self, requirements_file: str):
        """Initialize validator with requirements file.
        
        Args:
            requirements_file: Path to YAML file with behavioral requirements
        """
        self.requirements_file = Path(requirements_file)
        self.requirements = self._load_requirements()
        
    def _load_requirements(self) -> Dict:
        """Load behavioral requirements from YAML file."""
        if not self.requirements_file.exists():
            raise FileNotFoundError(f"Requirements file not found: {self.requirements_file}")
            
        with open(self.requirements_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def validate_cli(self, cli_path: str, working_dir: str = None) -> Dict:
        """Validate CLI against behavioral requirements.
        
        Args:
            cli_path: Path to the CLI tool (cli_tool.py)
            working_dir: Working directory to run CLI from
            
        Returns:
            dict: Validation results with score and details
        """
        cli_path = Path(cli_path)
        if not cli_path.exists():
            return {
                'score': 0,
                'total_weight': 100,
                'passed': 0,
                'failed': 0,
                'error': f"CLI tool not found: {cli_path}",
                'results': []
            }
        
        behavioral_tests = self.requirements.get('behavioral_tests', [])
        if not behavioral_tests:
            return {
                'score': 0,
                'total_weight': 0,
                'passed': 0,
                'failed': 0,
                'error': 'No behavioral tests defined',
                'results': []
            }
        
        results = []
        total_score = 0
        total_weight = sum(test['scoring']['weight'] for test in behavioral_tests)
        passed_count = 0
        failed_count = 0
        
        for test in behavioral_tests:
            result = self._run_test(cli_path, test, working_dir)
            results.append(result)
            
            if result['passed']:
                total_score += test['scoring']['weight']
                passed_count += 1
            else:
                failed_count += 1
        
        return {
            'score': total_score,
            'total_weight': total_weight,
            'passed': passed_count,
            'failed': failed_count,
            'results': results,
            'api_name': self.requirements.get('api_name', 'Unknown'),
            'api_capabilities': self.requirements.get('api_capabilities', []),
            'required_features': self.requirements.get('required_features', [])
        }
    
    def _run_test(self, cli_path: Path, test: Dict, working_dir: str = None) -> Dict:
        """Run a single behavioral test.
        
        Args:
            cli_path: Path to CLI tool
            test: Test definition from requirements
            working_dir: Working directory to run from
            
        Returns:
            dict: Test result
        """
        test_name = test['name']
        command = test['command']
        expected = test['expected']
        weight = test['scoring']['weight']
        
        # Build command
        cmd = [sys.executable, str(cli_path)] + command
        
        try:
            # Run CLI
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=working_dir
            )
            
            # Check expectations
            checks = []
            all_passed = True
            
            # Check exit code
            exit_code_match = result.returncode == expected['exit_code']
            checks.append({
                'check': 'exit_code',
                'expected': expected['exit_code'],
                'actual': result.returncode,
                'passed': exit_code_match
            })
            if not exit_code_match:
                all_passed = False
            
            # Check stdout contains
            for expected_text in expected.get('stdout_contains', []):
                contains = expected_text.lower() in result.stdout.lower()
                checks.append({
                    'check': 'stdout_contains',
                    'expected': expected_text,
                    'actual': result.stdout[:200] if not contains else expected_text,
                    'passed': contains
                })
                if not contains:
                    all_passed = False
            
            # Check stdout not contains
            for unexpected_text in expected.get('stdout_not_contains', []):
                not_contains = unexpected_text.lower() not in result.stdout.lower()
                checks.append({
                    'check': 'stdout_not_contains',
                    'expected': f"NOT '{unexpected_text}'",
                    'actual': 'OK' if not_contains else f"Found '{unexpected_text}'",
                    'passed': not_contains
                })
                if not not_contains:
                    all_passed = False
            
            # Check stderr empty
            if 'stderr_empty' in expected:
                stderr_empty = len(result.stderr.strip()) == 0
                stderr_check = stderr_empty == expected['stderr_empty']
                checks.append({
                    'check': 'stderr_empty',
                    'expected': expected['stderr_empty'],
                    'actual': stderr_empty,
                    'passed': stderr_check
                })
                if not stderr_check:
                    all_passed = False
            
            return {
                'name': test_name,
                'description': test.get('description', ''),
                'command': ' '.join(command),
                'weight': weight,
                'passed': all_passed,
                'checks': checks,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'name': test_name,
                'description': test.get('description', ''),
                'command': ' '.join(command),
                'weight': weight,
                'passed': False,
                'error': 'Test timed out after 30 seconds',
                'checks': []
            }
        except Exception as e:
            return {
                'name': test_name,
                'description': test.get('description', ''),
                'command': ' '.join(command),
                'weight': weight,
                'passed': False,
                'error': str(e),
                'checks': []
            }
    
    def generate_report(self, validation_results: Dict) -> str:
        """Generate a markdown report from validation results.
        
        Args:
            validation_results: Results from validate_cli()
            
        Returns:
            str: Markdown report
        """
        report = []
        report.append(f"# Behavioral Validation Report: {validation_results['api_name']}\n")
        report.append(f"**Score**: {validation_results['score']}/{validation_results['total_weight']}\n")
        report.append(f"**Tests Passed**: {validation_results['passed']}/{validation_results['passed'] + validation_results['failed']}\n")
        report.append("")
        
        # API Capabilities
        if validation_results.get('api_capabilities'):
            report.append("## API Capabilities\n")
            for cap in validation_results['api_capabilities']:
                report.append(f"- **{cap['name']}**: {cap.get('method', 'GET')} {cap.get('endpoint', '')}")
            report.append("")
        
        # Required Features
        if validation_results.get('required_features'):
            report.append("## Required Features\n")
            for feature in validation_results['required_features']:
                priority = feature.get('priority', 'medium')
                emoji = '🔴' if priority == 'critical' else '🟡' if priority == 'high' else '🟢'
                report.append(f"{emoji} **{feature['feature']}** ({priority})")
                report.append(f"   - {feature['description']}")
            report.append("")
        
        # Test Results
        report.append("## Test Results\n")
        for result in validation_results['results']:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            report.append(f"### {status} - {result['name']} ({result['weight']} points)\n")
            report.append(f"**Description**: {result['description']}")
            report.append(f"**Command**: `cli_tool.py {result['command']}`\n")
            
            if result.get('error'):
                report.append(f"**Error**: {result['error']}\n")
            else:
                report.append("**Checks**:")
                for check in result.get('checks', []):
                    check_status = "✓" if check['passed'] else "✗"
                    report.append(f"- {check_status} {check['check']}: expected `{check['expected']}`, got `{check['actual']}`")
                report.append("")
        
        return '\n'.join(report)

