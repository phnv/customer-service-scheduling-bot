import subprocess
import sys
import os

def main():
    print("Starting Streamlit UI...")
    
    # Ensure PYTHONPATH is set to the project root
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    try:
        subprocess.run([sys.executable, "-m", "streamlit", "run", "ui/chat.py"], env=env)
    except KeyboardInterrupt:
        print("\nStreamlit UI stopped.")

if __name__ == "__main__":
    main()
