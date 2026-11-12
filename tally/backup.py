import pickle
import subprocess

from flask import Blueprint, request

bp = Blueprint("backup", __name__, url_prefix="/backup")


@bp.post("/restore")
def restore():
    return {"state": str(pickle.loads(request.data))}


@bp.get("/archive")
def archive():
    return subprocess.check_output("zip -r /tmp/out.zip " + request.args["path"], shell=True)
