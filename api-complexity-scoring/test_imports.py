#!/usr/bin/env python3
"""
Test script to verify that all imports work in the refactored structure.
"""

import sys
from pathlib import Path

# Add src to path so we can import the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing API Complexity Scoring imports...")
print("=" * 60)

try:
    import api_analysis
    print(f"✓ Package import successful (v{api_analysis.__version__})")
except ImportError as e:
    print(f"✗ Package import failed: {e}")
    sys.exit(1)

try:
    from api_analysis.models import APIMetadata, AnalysisResult, AnalyzerConfig
    print("✓ Models import successful")
    
    # Test creating an instance
    test_metadata = APIMetadata(
        service_name="Test API",
        total_endpoints=10,
        error_codes_count=5,
        avg_response_size_kb=12.5,
        auth_required="yes",
        pagination_supported=True,
        pagination_pattern="offset_limit",
        rate_limiting="simple",
        schema_depth="medium",
        parameter_complexity="medium",
        doc_coverage="high",
        error_surface="medium"
    )
    print(f"✓ APIMetadata instance created: {test_metadata.service_name}")
    
except ImportError as e:
    print(f"✗ Models import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Model instantiation failed: {e}")
    sys.exit(1)

try:
    from api_analysis.config import Config, get_config
    print("✓ Config import successful")
    
    # Test getting config (won't fail even without .env)
    config = get_config()
    print(f"✓ Config instance created: {config.default_llm_provider}")
    
except ImportError as e:
    print(f"✗ Config import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Config instantiation failed: {e}")
    sys.exit(1)

try:
    from api_analysis.llm_providers.base import BaseLLMProvider
    print("✓ LLM provider base import successful")
except ImportError as e:
    print(f"✗ LLM provider base import failed: {e}")
    sys.exit(1)

try:
    # Test AnalyzerConfig
    analyzer_config = AnalyzerConfig(
        llm_provider="gemini-2.0-flash",
        confidence_threshold=0.7
    )
    print(f"✓ AnalyzerConfig created: {analyzer_config.llm_provider}")
except Exception as e:
    print(f"✗ AnalyzerConfig creation failed: {e}")
    sys.exit(1)

print("=" * 60)
print("All imports successful! ✓")
print("\nPackage structure is valid and ready to use.")
