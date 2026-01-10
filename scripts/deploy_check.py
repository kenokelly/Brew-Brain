import sys
import os

# Ensure we can import from app
sys.path.append(os.getcwd())

try:
    from app.qat.runner import QATRunner
except ImportError:
    print("❌ Error: Could not import QATRunner. Run from project root.")
    sys.exit(1)

def deploy():
    print("🔒 Starting Pre-Deployment Self-Check (QAT)...")
    print("---------------------------------------------")
    
    runner = QATRunner()
    report = runner.run_suite()
    
    for test in report['tests']:
        icon = "✅" if test['status'] == "PASS" else "❌"
        print(f"{icon} {test['name']}: {test['message']}")
        
    print("---------------------------------------------")
    
    if report['failed'] > 0:
        print(f"🛑 DEPLOYMENT ABORTED: {report['failed']} Tests Failed.")
        sys.exit(1)
    else:
        print("🚀 Systems Nominal. QAT Passed.")
        
        # TELEGRAM NOTIFICATION
        try:
            from app.services.notifications import send_telegram_message
            send_telegram_message("🚀 *DEPLOYMENT SUCCESS*\n\nBrew-Brain v2.0 is online.\nAll systems (ML, Sourcing, QAT) are nominal.")
        except Exception as e:
            print(f"Warning: Could not send Telegram: {e}")
            
        print("✅ Deploying Brew-Brain v2.0...")
        # In a real scenario, this would trigger the actual start command
        # e.g. os.system("gunicorn main:app")
        sys.exit(0)

if __name__ == "__main__":
    deploy()
