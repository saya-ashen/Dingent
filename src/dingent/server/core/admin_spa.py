# import os
# from importlib.resources import files
# from fastapi import APIRouter
# from fastapi.responses import FileResponse, RedirectResponse
#
# router = APIRouter()
# static_root = files("dingent").joinpath("static", "admin_dashboard")
# static_root_str = str(static_root)
#
#
# @router.get("/dashboard", include_in_schema=False)
# async def admin_redirect():
#     return RedirectResponse("/dashboard/")
#
#
# @router.get("/dashboard/{path:path}", include_in_schema=False)
# async def serve_admin_spa(path: str):
#     root_index_path = os.path.join(static_root_str, "index.html")
#     potential_file_path = os.path.join(static_root_str, path)
#
#     if os.path.isfile(potential_file_path):
#         return FileResponse(potential_file_path)
#
#     potential_html_path = os.path.join(static_root_str, f"{path}.html")
#     if os.path.isfile(potential_html_path):
#         return FileResponse(potential_html_path)
#
#     # Fallback for SPA client-side routing
#     return FileResponse(root_index_path)
