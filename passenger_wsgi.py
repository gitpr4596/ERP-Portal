# import os, sys, traceback
# sys.path.insert(0, os.path.dirname(__file__))  # import from /erp

# try:
#     # Your normal import path
#     from wsgi import application
# except Exception as e:
#     tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
#     def application(environ, start_response):
#         start_response('500 Internal Server Error',
#                       [('Content-Type', 'text/plain; charset=utf-8')])
#         return [(f"WSGI boot error (import failed):\n\n{tb}").encode("utf-8")]
# passenger_wsgi.py (RESTORE THIS AFTER TEST)
import os, sys, traceback
sys.stdout = sys.stderr
APP_ROOT = os.path.dirname(__file__)
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

cred_path = os.path.join(APP_ROOT, "credentials.json")
if os.path.exists(cred_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_path

def _capture():
    try:
        with open(os.path.join(APP_ROOT, "startup_error.log"), "a") as f:
            f.write("\n" + "="*80 + "\nSTARTUP CRASH\n\n")
            traceback.print_exc(file=f)
    except Exception:
        pass

try:
    from wsgi import application   # your wsgi.py -> from app import app as application
except Exception:
    _capture()
    import traceback
    tb = traceback.format_exc()
    def application(environ, start_response):
        start_response("500 Internal Server Error",
                       [("Content-Type", "text/plain; charset=utf-8")])
        return [("WSGI boot error (import failed):\n\n" + tb).encode("utf-8")]
