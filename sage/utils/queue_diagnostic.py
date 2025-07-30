#!/usr/bin/env python3
"""
Queue System Diagnostic Tool

Diagnoses queue backend issues and provides recommendations for fixing them.
"""

import sys
import os
import logging
from typing import Dict, Any, List

# Add SAGE root to Python path
SAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if SAGE_ROOT not in sys.path:
    sys.path.insert(0, SAGE_ROOT)

def setup_logging():
    """Setup logging for diagnostics"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    return logging.getLogger(__name__)

def diagnose_queue_backends() -> Dict[str, Any]:
    """Comprehensive diagnosis of queue backends"""
    logger = setup_logging()
    
    diagnosis = {
        "overall_status": "unknown",
        "recommendations": [],
        "errors": [],
        "backend_status": {},
        "environment": {}
    }
    
    try:
        # Check environment
        diagnosis["environment"] = check_environment()
        
        # Check each backend
        diagnosis["backend_status"] = check_all_backends()
        
        # Generate recommendations
        diagnosis["recommendations"] = generate_recommendations(
            diagnosis["environment"], 
            diagnosis["backend_status"]
        )
        
        # Determine overall status
        working_backends = [
            name for name, status in diagnosis["backend_status"].items() 
            if status.get("working", False)
        ]
        
        if len(working_backends) >= 2:
            diagnosis["overall_status"] = "good"
        elif len(working_backends) == 1:
            diagnosis["overall_status"] = "limited"
        else:
            diagnosis["overall_status"] = "critical"
            
    except Exception as e:
        diagnosis["errors"].append(f"Diagnosis failed: {e}")
        diagnosis["overall_status"] = "error"
    
    return diagnosis

def check_environment() -> Dict[str, Any]:
    """Check the current environment"""
    env_info = {
        "python_version": sys.version,
        "ray_initialized": False,
        "ray_available": False,
        "sage_environment": False,
        "distributed_mode": False
    }
    
    # Check Ray
    try:
        import ray
        env_info["ray_available"] = True
        env_info["ray_initialized"] = ray.is_initialized()
        env_info["distributed_mode"] = ray.is_initialized()
    except ImportError:
        pass
    
    # Check SAGE environment
    try:
        # Add SAGE to path if needed
        import os
        sage_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if sage_root not in sys.path:
            sys.path.insert(0, sage_root)
            
        import sage
        env_info["sage_environment"] = True
    except ImportError:
        pass
    
    return env_info

def check_all_backends() -> Dict[str, Dict[str, Any]]:
    """Check all queue backends"""
    backends = {}
    
    # Check SAGE queue
    backends["sage_queue"] = check_sage_queue()
    
    # Check Ray queue
    backends["ray_queue"] = check_ray_queue()
    
    # Check Python queue
    backends["python_queue"] = check_python_queue()
    
    return backends

def check_sage_queue() -> Dict[str, Any]:
    """Check SAGE queue backend"""
    status = {
        "available": False,
        "working": False,
        "distributed_support": False,
        "error": None,
        "details": {}
    }
    
    try:
        # Add SAGE to path if needed
        import sys
        import os
        sage_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if sage_root not in sys.path:
            sys.path.insert(0, sage_root)
        
        # Try importing - use absolute import
        try:
            from sage_ext.sage_queue.python.sage_queue import SageQueue
        except ImportError:
            # Alternative import path
            import sage_ext.sage_queue.python.sage_queue as sage_queue_module
            SageQueue = sage_queue_module.SageQueue
        
        status["available"] = True
        
        # Try creating and using a queue
        test_queue = SageQueue(name="diagnostic_test", maxsize=10)
        test_queue.put("test_message")
        result = test_queue.get()
        test_queue.close()
        
        if result == "test_message":
            status["working"] = True
        else:
            status["error"] = "Queue test failed - data mismatch"
            
        # SAGE queue doesn't support distributed environments
        status["distributed_support"] = False
        status["details"]["supports_multiprocess"] = True
        status["details"]["high_performance"] = True
        
    except ImportError as e:
        status["error"] = f"Import failed: {e}"
    except Exception as e:
        status["available"] = True
        status["error"] = f"Runtime error: {e}"
    
    return status

def check_ray_queue() -> Dict[str, Any]:
    """Check Ray queue backend"""
    status = {
        "available": False,
        "working": False,
        "distributed_support": True,
        "error": None,
        "details": {}
    }
    
    try:
        # Add SAGE to path if needed
        import sys
        import os
        sage_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if sage_root not in sys.path:
            sys.path.insert(0, sage_root)
        
        # Try importing Ray
        import ray
        from ray.util.queue import Queue as RayQueue
        status["available"] = True
        
        # Initialize Ray if needed
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
        
        # Try creating and using a queue
        test_queue = RayQueue(maxsize=10)
        test_queue.put("test_message")
        result = test_queue.get()
        
        if result == "test_message":
            status["working"] = True
        else:
            status["error"] = "Queue test failed - data mismatch"
            
        status["details"]["supports_distributed"] = True
        status["details"]["supports_multiprocess"] = True
        status["details"]["ray_version"] = ray.__version__
        
    except ImportError as e:
        status["error"] = f"Import failed: {e}"
    except Exception as e:
        status["available"] = True
        status["error"] = f"Runtime error: {e}"
    
    return status

def check_python_queue() -> Dict[str, Any]:
    """Check Python standard queue"""
    status = {
        "available": False,
        "working": False,
        "distributed_support": False,
        "error": None,
        "details": {}
    }
    
    try:
        # Add SAGE to path if needed
        import sys
        import os
        sage_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if sage_root not in sys.path:
            sys.path.insert(0, sage_root)
            
        import queue
        status["available"] = True
        
        # Try creating and using a queue
        test_queue = queue.Queue(maxsize=10)
        test_queue.put("test_message")
        result = test_queue.get()
        
        if result == "test_message":
            status["working"] = True
        else:
            status["error"] = "Queue test failed - data mismatch"
            
        status["details"]["basic_fallback"] = True
        
    except Exception as e:
        status["error"] = f"Error: {e}"
    
    return status

def generate_recommendations(env_info: Dict[str, Any], backend_status: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on diagnosis"""
    recommendations = []
    
    # Check if we have any working backends
    working_backends = [name for name, status in backend_status.items() if status.get("working", False)]
    
    if not working_backends:
        recommendations.append("❌ CRITICAL: No working queue backends found!")
        recommendations.append("   • Install Ray: pip install ray")
        recommendations.append("   • Build SAGE extension: cd sage_ext/sage_queue && ./build.sh")
        return recommendations
    
    # Environment-specific recommendations
    if env_info.get("distributed_mode", False):
        if "ray_queue" not in working_backends:
            recommendations.append("⚠️  Ray queue not working in distributed environment")
            recommendations.append("   • Check Ray installation and initialization")
        else:
            recommendations.append("✅ Ray queue working - good for distributed environment")
    else:
        # Local environment
        if "sage_queue" not in working_backends:
            recommendations.append("💡 SAGE queue not available for high-performance local processing")
            recommendations.append("   • Build SAGE extension: cd sage_ext/sage_queue && ./build.sh")
        else:
            recommendations.append("✅ SAGE queue working - excellent for local high-performance processing")
    
    # Fallback analysis
    if len(working_backends) == 1:
        recommendations.append(f"⚠️  Only one backend working: {working_backends[0]}")
        recommendations.append("   • Consider installing additional backends for redundancy")
    
    # Performance recommendations
    if env_info.get("distributed_mode", False) and "sage_queue" in working_backends:
        recommendations.append("⚠️  SAGE queue doesn't support distributed environments")
        recommendations.append("   • Will automatically fallback to Ray queue for distributed tasks")
    
    return recommendations

def print_diagnosis_report(diagnosis: Dict[str, Any]):
    """Print a formatted diagnosis report"""
    print("🔍 SAGE Queue System Diagnosis Report")
    print("=" * 50)
    
    # Overall status
    status_emoji = {
        "good": "✅",
        "limited": "⚠️ ",
        "critical": "❌",
        "error": "💥"
    }
    overall_status = diagnosis["overall_status"]
    print(f"\n📊 Overall Status: {status_emoji.get(overall_status, '❓')} {overall_status.upper()}")
    
    # Environment info
    print(f"\n🌍 Environment:")
    env = diagnosis["environment"]
    print(f"   • Python: {env.get('python_version', 'Unknown')[:20]}...")
    print(f"   • Ray Available: {'✅' if env.get('ray_available') else '❌'}")
    print(f"   • Ray Initialized: {'✅' if env.get('ray_initialized') else '❌'}")
    print(f"   • SAGE Environment: {'✅' if env.get('sage_environment') else '❌'}")
    print(f"   • Distributed Mode: {'✅' if env.get('distributed_mode') else '❌'}")
    
    # Backend status
    print(f"\n🔧 Backend Status:")
    for name, status in diagnosis["backend_status"].items():
        working = status.get("working", False)
        available = status.get("available", False)
        distributed = status.get("distributed_support", False)
        
        icon = "✅" if working else ("⚠️ " if available else "❌")
        dist_icon = "🌐" if distributed else "🏠"
        
        print(f"   • {name}: {icon} {'Working' if working else ('Available' if available else 'Not Available')} {dist_icon}")
        
        if status.get("error"):
            print(f"     Error: {status['error']}")
    
    # Recommendations
    if diagnosis["recommendations"]:
        print(f"\n💡 Recommendations:")
        for rec in diagnosis["recommendations"]:
            print(f"   {rec}")
    
    # Errors
    if diagnosis["errors"]:
        print(f"\n❌ Errors:")
        for error in diagnosis["errors"]:
            print(f"   • {error}")
    
    print(f"\n" + "=" * 50)

def main():
    """Main function for command-line usage"""
    print("🚀 Starting SAGE Queue System Diagnosis...")
    
    try:
        diagnosis = diagnose_queue_backends()
        print_diagnosis_report(diagnosis)
        
        # Exit with appropriate code
        if diagnosis["overall_status"] == "critical":
            sys.exit(1)
        elif diagnosis["overall_status"] == "limited":
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(3)

if __name__ == "__main__":
    main()
