import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../python'))
from notebook1 import run_notebook1

def handler(request):
    try:
        if request.method == "POST":
            # You can parse POST data here if needed
            # For now, just run with default/test values
            result = run_notebook1('pdf', 'yourfile.pdf', 'input.wav')  # Adjust as needed
            return {
                "statusCode": 200,
                "body": json.dumps(result)
            }
        else:
            return {
                "statusCode": 405,
                "body": json.dumps({"error": "Method not allowed"})
            }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        } 