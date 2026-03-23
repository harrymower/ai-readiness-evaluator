#!/usr/bin/env python3
"""
Command-line interface for API complexity scoring.

Usage:
    python -m api_analysis analyze "curl https://api.example.com/endpoint"
    python -m api_analysis analyze --file curl_commands.txt
"""

import json
import sys
from pathlib import Path

# Add src to path if running as script
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent / 'src'))

from api_analysis.analyzers.programmatic import (
    analyze_api_programmatically,
    analyze_multiple_endpoints
)
from api_analysis.fetchers import fetch_and_clean_documentation
from api_analysis.analyzers.llm import analyze_with_llm
from api_analysis.validators.merger import validate_and_merge
from api_analysis.outputs.yaml_generator import generate_yaml_file
from api_analysis.config import get_config


def print_results(results: dict, verbose: bool = False):
    """Pretty print analysis results."""
    print("\n" + "=" * 70)
    print("API Complexity Analysis Results")
    print("=" * 70)
    
    if results.get('error'):
        print(f"\n❌ Error: {results['error']}\n")
        return
    
    # Handle AnalysisResult objects
    if hasattr(results, 'metadata'):
        metadata = results.metadata.model_dump()
        print(f"\n📊 Metadata ({results.source} analysis):")
        for key, value in metadata.items():
            print(f"   {key:25} {value}")
        
        print(f"\n🎯 Confidence (avg: {results.average_confidence:.2f}):")
        for field, conf in results.confidence_scores.items():
            print(f"   {field:25} {conf:.2f}")
        
        if results.flags:
            print(f"\n⚠️  Flags:")
            for flag in results.flags:
                print(f"   - {flag}")
        
        if verbose and results.reasoning:
            print(f"\n📝 Reasoning:")
            for field, reason in results.reasoning.items():
                print(f"   {field}: {reason}")
    else:
        # Original format for programmatic-only results
        print(f"\n📊 Metrics:")
        print(f"   Status Code:        {results.get('status_code', 'N/A')}")
        print(f"   Response Size:      {results.get('avg_response_size_kb', 0)} KB")
        print(f"   Schema Depth:       {results.get('schema_depth', 'unknown')}")
        print(f"   Pagination:         {results.get('pagination_supported', False)} ({results.get('pagination_pattern', 'none')})")
        print(f"   Rate Limiting:      {results.get('rate_limiting', 'none')}")
        print(f"   Auth Required:      {results.get('auth_detected', False) or results.get('auth_required', 'unknown')}")
        
        if 'total_endpoints' in results:
            print(f"   Total Endpoints:    {results['total_endpoints']}")
        
        if verbose:
            print(f"\n📝 Raw Results:")
            print(json.dumps(results, indent=2))
    
    print("\n" + "=" * 70 + "\n")


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Analyze API complexity programmatically',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single endpoint
  python cli.py analyze "curl https://api.github.com/users/octocat"
  
  # Analyze with custom timeout
  python cli.py analyze "curl https://api.github.com/repos" --timeout 60
  
  # Analyze multiple endpoints from file
  python cli.py analyze --file commands.txt
  
  # Show verbose output
  python cli.py analyze "curl https://api.github.com" --verbose
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze an API endpoint')
    analyze_parser.add_argument(
        'curl_command',
        nargs='?',
        help='Curl command to analyze'
    )
    analyze_parser.add_argument(
        '--file', '-f',
        help='File containing curl commands (one per line)'
    )
    analyze_parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Request timeout in seconds (default: 30)'
    )
    analyze_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output including raw results'
    )
    analyze_parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    analyze_parser.add_argument(
        '--full',
        action='store_true',
        help='Run full analysis pipeline (programmatic + LLM + merge)'
    )
    analyze_parser.add_argument(
        '--doc-url',
        help='Documentation URL to fetch and analyze (used with --full)'
    )
    analyze_parser.add_argument(
        '--output-yaml',
        help='Output YAML file path for results (used with --full)'
    )
    analyze_parser.add_argument(
        '--llm-provider',
        default='gemini-2.0-flash',
        choices=['gemini-2.0-flash', 'gpt-4o-mini'],
        help='LLM provider to use (default: gemini-2.0-flash)'
    )
    analyze_parser.add_argument(
        '--api-name',
        help='API name for analysis (default: extracted from URL)'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'analyze':
        if args.full:
            # Run full pipeline
            if not args.curl_command:
                print("❌ Please provide a curl command for full analysis")
                sys.exit(1)
            
            api_name = args.api_name or "API"
            config = get_config()
            
            try:
                # Step 1: Programmatic analysis
                print("\n🔍 Step 1/3: Running programmatic analysis...")
                prog_results = analyze_api_programmatically(args.curl_command, timeout=args.timeout)
                
                if prog_results.get('error'):
                    print(f"❌ Programmatic analysis failed: {prog_results['error']}")
                    sys.exit(1)
                
                # Step 2: Fetch documentation (if provided)
                doc_content = ""
                if args.doc_url:
                    print(f"\n📄 Step 2/3: Fetching documentation from {args.doc_url}...")
                    doc_result = fetch_and_clean_documentation(args.doc_url, timeout=args.timeout)
                    
                    if doc_result['error']:
                        print(f"⚠️  Documentation fetch failed: {doc_result['error']}")
                        print("   Continuing with programmatic analysis only...")
                    else:
                        doc_content = doc_result['content']
                        print(f"   ✓ Documentation type: {doc_result['type']}")
                        if doc_result['openapi_url']:
                            print(f"   ✓ OpenAPI spec found: {doc_result['openapi_url']}")
                else:
                    print("\n⚠️  No documentation URL provided, using programmatic analysis only")
                
                # Step 3: LLM analysis
                if not doc_content:
                    doc_content = f"API endpoint: {args.curl_command}\n\nNo documentation available."
                
                print(f"\n🤖 Step 3/3: Running LLM analysis with {args.llm_provider}...")
                try:
                    llm_result = analyze_with_llm(
                        api_name=api_name,
                        documentation=doc_content,
                        programmatic_results=prog_results,
                        llm_provider=args.llm_provider,
                        config=config
                    )
                    
                    # Step 4: Merge and validate
                    print("\n✅ Merging and validating results...")
                    final_result = validate_and_merge(
                        api_name=api_name,
                        programmatic=prog_results,
                        llm=llm_result,
                        confidence_threshold=config.confidence_threshold
                    )
                    
                    # Output
                    if args.output_yaml:
                        generate_yaml_file([final_result], args.output_yaml)
                        print(f"\n💾 Results saved to {args.output_yaml}")
                    
                    if args.json:
                        print(json.dumps(final_result.to_dict(), indent=2))
                    else:
                        print_results(final_result, verbose=args.verbose)
                    
                except Exception as e:
                    print(f"❌ LLM analysis failed: {e}")
                    print("   Falling back to programmatic results only...")
                    print_results(prog_results, verbose=args.verbose)
                    sys.exit(1)
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                if args.verbose:
                    traceback.print_exc()
                sys.exit(1)
        
        elif args.file:
            # Analyze multiple endpoints from file
            try:
                with open(args.file, 'r') as f:
                    commands = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                if not commands:
                    print("❌ No valid curl commands found in file")
                    sys.exit(1)
                
                print(f"\n📁 Analyzing {len(commands)} endpoints from {args.file}...")
                results = analyze_multiple_endpoints(commands, timeout=args.timeout)
                
                if args.json:
                    print(json.dumps(results, indent=2))
                else:
                    print_results(results, verbose=args.verbose)
                    
            except FileNotFoundError:
                print(f"❌ File not found: {args.file}")
                sys.exit(1)
            except Exception as e:
                print(f"❌ Error reading file: {e}")
                sys.exit(1)
        
        elif args.curl_command:
            # Analyze single endpoint (programmatic only)
            print(f"\n🔍 Analyzing API endpoint...")
            results = analyze_api_programmatically(args.curl_command, timeout=args.timeout)
            
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                print_results(results, verbose=args.verbose)
        
        else:
            print("❌ Please provide either a curl command or --file option")
            analyze_parser.print_help()
            sys.exit(1)


if __name__ == '__main__':
    main()
