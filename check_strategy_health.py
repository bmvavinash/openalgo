"""
Strategy Health Check
Comprehensive analysis of all strategies for issues and improvements
"""
import sys
import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def get_strategy_files() -> List[Path]:
    """Get all strategy Python files"""
    strategies_dir = PROJECT_ROOT / 'strategies' / 'scripts'
    if not strategies_dir.exists():
        return []

    return list(strategies_dir.glob('*.py'))


def analyze_strategy_file(file_path: Path) -> Dict:
    """Analyze a single strategy file for issues and improvements"""
    try:
        content = file_path.read_text(encoding='utf-8')

        issues = []
        suggestions = []
        warnings = []

        # Parse AST for deeper analysis
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
            return {
                'file': file_path.name,
                'issues': issues,
                'suggestions': suggestions,
                'warnings': warnings,
                'health_score': 0
            }

        # Check for stop loss implementation
        stop_loss_keywords = ['stop_loss', 'stoploss', 'sl', 'trigger_price']
        has_stop_loss = any(keyword.lower() in content.lower() for keyword in stop_loss_keywords)

        if not has_stop_loss:
            issues.append("Missing stop loss implementation - critical risk management issue")

        # Check for risk management
        risk_keywords = ['risk', 'position_size', 'max_loss', 'take_profit']
        has_risk_management = any(keyword.lower() in content.lower() for keyword in risk_keywords)

        if not has_risk_management:
            warnings.append("No explicit risk management - consider adding position sizing")

        # Check for proper error handling
        has_try_except = 'try:' in content and 'except' in content
        if not has_try_except:
            suggestions.append("Add proper error handling with try/except blocks")

        # Check for logging
        has_logging = 'logger.' in content or 'logging.' in content
        if not has_logging:
            suggestions.append("Add proper logging for debugging and monitoring")

        # Check for configuration loading
        has_config = 'get_config' in content
        if not has_config:
            warnings.append("Not using centralized configuration - consider using config_loader")

        # Check for API key handling
        has_api_key = 'API_KEY' in content or 'api_key' in content
        if not has_api_key:
            warnings.append("No API key configuration found")

        # Check for position tracking
        has_position_tracking = 'positions' in content and ('BUY' in content or 'SELL' in content)
        if not has_position_tracking:
            issues.append("Missing position tracking - essential for strategy state")

        # Check for data validation
        has_data_validation = 'empty' in content or 'isna' in content or 'notna' in content
        if not has_data_validation:
            suggestions.append("Add data validation before signal calculation")

        # Check for reasonable sleep intervals (not too aggressive)
        sleep_matches = re.findall(r'sleep\((\d+)\)', content)
        if sleep_matches:
            min_sleep = min(int(x) for x in sleep_matches)
            if min_sleep < 30:
                warnings.append(f"Very aggressive polling (sleep {min_sleep}s) - may hit rate limits")

        # Check for proper imports
        required_imports = ['pandas', 'numpy']
        missing_imports = []
        for imp in required_imports:
            if f'import {imp}' not in content and f'from {imp}' not in content:
                missing_imports.append(imp)

        if missing_imports:
            warnings.append(f"Missing recommended imports: {', '.join(missing_imports)}")

        # Check for strategy parameters configuration
        strategy_params = re.findall(r'(\w+)\s*=\s*strategy_config\.get\([^,]+,\s*([^)]+)\)', content)
        if not strategy_params:
            suggestions.append("Consider making strategy parameters configurable via config file")

        # Calculate health score (0-100)
        health_score = 100

        # Critical issues (-30 each)
        health_score -= len(issues) * 30

        # Warnings (-10 each)
        health_score -= len(warnings) * 10

        # Suggestions (-5 each)
        health_score -= len(suggestions) * 5

        # Bonus for good practices
        if has_stop_loss:
            health_score += 15
        if has_risk_management:
            health_score += 10
        if has_logging:
            health_score += 5
        if has_config:
            health_score += 5
        if has_try_except:
            health_score += 5

        health_score = max(0, min(100, health_score))

        return {
            'file': file_path.name,
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions,
            'health_score': health_score,
            'features': {
                'stop_loss': has_stop_loss,
                'risk_management': has_risk_management,
                'error_handling': has_try_except,
                'logging': has_logging,
                'config': has_config,
                'position_tracking': has_position_tracking,
                'data_validation': has_data_validation
            }
        }

    except Exception as e:
        return {
            'file': file_path.name,
            'issues': [f"Analysis failed: {e}"],
            'warnings': [],
            'suggestions': [],
            'health_score': 0,
            'features': {}
        }


def generate_health_report(results: List[Dict]) -> None:
    """Generate comprehensive health report"""
    print("\n" + "="*120)
    print("🩺 STRATEGY HEALTH CHECK REPORT")
    print("="*120)

    if not results:
        print("\n❌ No strategies found to analyze")
        return

    # Sort by health score
    results.sort(key=lambda x: x['health_score'], reverse=True)

    # Overall statistics
    total_strategies = len(results)
    healthy_strategies = len([r for r in results if r['health_score'] >= 80])
    problematic_strategies = len([r for r in results if r['health_score'] < 60])

    print(f"\n📊 OVERVIEW")
    print(f"Total Strategies: {total_strategies}")
    print(f"Healthy (≥80%): {healthy_strategies}")
    print(f"Problematic (<60%): {problematic_strategies}")

    # Individual strategy analysis
    print(f"\n{'─'*120}")
    print("📋 INDIVIDUAL STRATEGY ANALYSIS")
    print(f"{'─'*120}")

    for result in results:
        score = result['health_score']
        if score >= 80:
            status_icon = "✅"
            status_color = "HEALTHY"
        elif score >= 60:
            status_icon = "⚠️"
            status_color = "FAIR"
        else:
            status_icon = "❌"
            status_color = "CRITICAL"

        print(f"\n{status_icon} {result['file']}")
        print(f"   Health Score: {score}% ({status_color})")

        # Features
        features = result['features']
        feature_list = []
        if features.get('stop_loss'):
            feature_list.append("🛡️ Stop Loss")
        if features.get('risk_management'):
            feature_list.append("📊 Risk Mgmt")
        if features.get('error_handling'):
            feature_list.append("🚨 Error Handling")
        if features.get('logging'):
            feature_list.append("📝 Logging")
        if features.get('config'):
            feature_list.append("⚙️ Config")
        if features.get('position_tracking'):
            feature_list.append("📍 Position Tracking")

        if feature_list:
            print(f"   Features: {', '.join(feature_list)}")

        # Issues
        if result['issues']:
            print(f"   🚨 Critical Issues ({len(result['issues'])}):")
            for issue in result['issues']:
                print(f"      • {issue}")

        # Warnings
        if result['warnings']:
            print(f"   ⚠️ Warnings ({len(result['warnings'])}):")
            for warning in result['warnings']:
                print(f"      • {warning}")

        # Suggestions
        if result['suggestions']:
            print(f"   💡 Suggestions ({len(result['suggestions'])}):")
            for suggestion in result['suggestions']:
                print(f"      • {suggestion}")

    # Recommendations summary
    print(f"\n{'─'*120}")
    print("🎯 RECOMMENDATIONS SUMMARY")
    print(f"{'─'*120}")

    all_issues = []
    all_warnings = []
    all_suggestions = []

    for result in results:
        all_issues.extend(result['issues'])
        all_warnings.extend(result['warnings'])
        all_suggestions.extend(result['suggestions'])

    # Most common issues
    if all_issues:
        print(f"\n🔴 TOP ISSUES TO FIX:")
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {count}x: {issue}")

    if all_warnings:
        print(f"\n🟡 COMMON WARNINGS:")
        warning_counts = {}
        for warning in all_warnings:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1

        for warning, count in sorted(warning_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {count}x: {warning}")

    if all_suggestions:
        print(f"\n💡 IMPROVEMENT SUGGESTIONS:")
        suggestion_counts = {}
        for suggestion in all_suggestions:
            suggestion_counts[suggestion] = suggestion_counts.get(suggestion, 0) + 1

        for suggestion, count in sorted(suggestion_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {count}x: {suggestion}")

    # Action plan
    print(f"\n{'─'*120}")
    print("📝 ACTION PLAN")
    print(f"{'─'*120}")

    print(f"\n1. IMMEDIATE FIXES (Critical Issues):")
    critical_strategies = [r for r in results if r['issues']]
    if critical_strategies:
        for result in critical_strategies:
            print(f"   • Fix {result['file']}: {', '.join(result['issues'])}")
    else:
        print(f"   ✅ No critical issues found")

    print(f"\n2. HIGH PRIORITY (Warnings):")
    warning_strategies = [r for r in results if r['warnings']]
    if warning_strategies:
        print(f"   • Address warnings in {len(warning_strategies)} strategies")
        print(f"   • Focus on risk management and configuration")
    else:
        print(f"   ✅ No warnings found")

    print(f"\n3. ENHANCEMENTS (Suggestions):")
    print(f"   • Consider adding logging and error handling")
    print(f"   • Implement data validation")
    print(f"   • Make parameters configurable")

    print(f"\n4. MONITORING:")
    print(f"   • Run this health check weekly")
    print(f"   • Monitor strategy performance daily")
    print(f"   • Update strategies based on market conditions")

    print(f"\n{'='*120}\n")


def main():
    """Main function"""
    print("\n" + "="*120)
    print("🩺 STRATEGY HEALTH CHECK")
    print("="*120)

    strategy_files = get_strategy_files()
    print(f"\nFound {len(strategy_files)} strategy files to analyze:")

    results = []
    for file_path in strategy_files:
        print(f"  📄 {file_path.name}")
        result = analyze_strategy_file(file_path)
        results.append(result)

    generate_health_report(results)

    # Summary
    avg_score = sum(r['health_score'] for r in results) / len(results) if results else 0
    print(f"\n{'='*120}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*120}")
    print(f"Average Health Score: {avg_score:.1f}%")

    if avg_score >= 80:
        print("✅ Overall: EXCELLENT - All strategies are well-implemented")
    elif avg_score >= 60:
        print("⚠️ Overall: GOOD - Minor improvements needed")
    else:
        print("❌ Overall: NEEDS ATTENTION - Critical issues to address")

    print(f"{'='*120}\n")


if __name__ == "__main__":
    main()






