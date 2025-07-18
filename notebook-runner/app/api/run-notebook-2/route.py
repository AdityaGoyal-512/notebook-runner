import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../python'))
from notebook2 import run_notebook2

def handler(request):
    try:
        if request.method == "POST":
            result = run_notebook2('pdf', 'yourfile.pdf', 'input.mp3')  # Adjust as needed
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