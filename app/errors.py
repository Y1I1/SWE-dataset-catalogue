from flask import flash, redirect, render_template, url_for


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def rate_limited(_error):
        flash("Too many requests. Please wait and try again.", "error")
        return redirect(url_for("auth.login"))
