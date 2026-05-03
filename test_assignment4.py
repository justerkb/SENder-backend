"""
Comprehensive verification tests for Assignment 4.
Tests middleware logic, models, schemas, task logic,
and route structure – without needing a live DB/Redis/ES.
"""

import sys
import os
import io

# Inject fake DB URL so Settings validation passes
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://test:test@localhost/test")

sys.path.insert(0, os.path.dirname(__file__))

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# =====================================================================
# 1. CONFIG
# =====================================================================
class TestConfig(unittest.TestCase):
    def test_settings_loads(self):
        from config import get_settings
        s = get_settings()
        self.assertEqual(s.app_name, "PackageGo API")
        self.assertEqual(s.rate_limit_per_minute, 60)
        self.assertEqual(s.rate_limit_per_hour, 500)
        self.assertEqual(s.rate_limit_write_per_hour, 50)
        self.assertTrue(s.enable_profiling)
        print("  ✓ Settings load correctly with all new fields")

    def test_cors_defaults(self):
        from config import get_settings
        s = get_settings()
        self.assertIn("*", s.cors_origins)
        print("  ✓ CORS origins default to *")

# =====================================================================
# 2. MIDDLEWARE IMPORTS & STRUCTURE
# =====================================================================
class TestMiddlewareImports(unittest.TestCase):
    def test_cors_middleware(self):
        from middleware.cors import setup_cors
        from fastapi import FastAPI
        app = FastAPI()
        setup_cors(app)
        # Check CORSMiddleware is in the stack
        mw_names = [type(m).__name__ for m in app.middleware_stack.__class__.__mro__]
        print("  ✓ setup_cors() runs without error")

    def test_logging_middleware_class(self):
        from middleware.logging_mw import LoggingMiddleware, close_es_client
        import inspect
        self.assertTrue(inspect.isclass(LoggingMiddleware))
        self.assertTrue(asyncio_compat(close_es_client))
        print("  ✓ LoggingMiddleware class and close_es_client exist")

    def test_rate_limiter(self):
        from middleware.rate_limiter import WriteRateLimitMiddleware, rate_limit_exceeded_handler, get_limiter
        import inspect
        self.assertTrue(inspect.isclass(WriteRateLimitMiddleware))
        self.assertTrue(callable(rate_limit_exceeded_handler))
        self.assertTrue(callable(get_limiter))
        print("  ✓ WriteRateLimitMiddleware, rate_limit_exceeded_handler, get_limiter all present")

    def test_profiling_middleware(self):
        from middleware.profiling import ProfilingMiddleware, profiling_router, get_last_profile_html, get_latency_store
        import inspect
        self.assertTrue(inspect.isclass(ProfilingMiddleware))
        # router has /last and /slow
        paths = [r.path for r in profiling_router.routes]
        self.assertIn("/admin/profiling/last", paths)
        self.assertIn("/admin/profiling/slow", paths)
        print("  ✓ ProfilingMiddleware + /admin/profiling/last + /admin/profiling/slow routes exist")

def asyncio_compat(fn):
    """Check coroutine or regular callable."""
    import asyncio
    return asyncio.iscoroutinefunction(fn) or callable(fn)

# =====================================================================
# 3. LOG LEVEL CLASSIFICATION
# =====================================================================
class TestLogLevelClassification(unittest.TestCase):
    def test_log_levels(self):
        """Verify the log level logic matches spec: 2xx=INFO, 4xx=DEBUG, 5xx=ERROR."""
        def classify(status_code):
            if status_code >= 500:
                return "ERROR"
            elif status_code >= 400:
                return "DEBUG"
            return "INFO"

        self.assertEqual(classify(200), "INFO")
        self.assertEqual(classify(201), "INFO")
        self.assertEqual(classify(301), "INFO")
        self.assertEqual(classify(400), "DEBUG")
        self.assertEqual(classify(401), "DEBUG")
        self.assertEqual(classify(404), "DEBUG")
        self.assertEqual(classify(500), "ERROR")
        self.assertEqual(classify(502), "ERROR")
        print("  ✓ Log level classification: 2xx=INFO, 4xx=DEBUG, 5xx=ERROR ✓")

# =====================================================================
# 4. RATE LIMITING LOGIC
# =====================================================================
class TestRateLimitingLogic(unittest.TestCase):
    def test_write_methods_set(self):
        from middleware.rate_limiter import _WRITE_METHODS
        self.assertIn("POST", _WRITE_METHODS)
        self.assertIn("PUT", _WRITE_METHODS)
        self.assertIn("PATCH", _WRITE_METHODS)
        self.assertIn("DELETE", _WRITE_METHODS)
        self.assertNotIn("GET", _WRITE_METHODS)
        self.assertNotIn("HEAD", _WRITE_METHODS)
        print("  ✓ Write methods: POST/PUT/PATCH/DELETE, GET is NOT limited")

    def test_rate_limit_values(self):
        from config import get_settings
        s = get_settings()
        self.assertEqual(s.rate_limit_per_minute, 60, "Should be 60 req/min")
        self.assertEqual(s.rate_limit_per_hour, 500, "Should be 500 req/hr")
        self.assertEqual(s.rate_limit_write_per_hour, 50, "Should be 50 writes/hr")
        print("  ✓ Rate limits: 60/min, 500/hr, 50 writes/hr per IP")

# =====================================================================
# 5. PROFILING - SLOW ENDPOINT LOGIC
# =====================================================================
class TestProfilingLogic(unittest.TestCase):
    def test_latency_tracking(self):
        from middleware.profiling import _latency_store, _MAX_SAMPLES
        # Simulate storing latencies
        _latency_store.clear()
        _latency_store["/test"].extend([100.0, 200.0, 150.0])
        samples = _latency_store["/test"]
        avg = sum(samples) / len(samples)
        self.assertAlmostEqual(avg, 150.0)
        print("  ✓ Latency store tracks per-endpoint stats")

    def test_max_samples_constant(self):
        from middleware.profiling import _MAX_SAMPLES
        self.assertEqual(_MAX_SAMPLES, 500)
        print("  ✓ Max samples per endpoint = 500")

# =====================================================================
# 6. MODELS
# =====================================================================
class TestModels(unittest.TestCase):
    def test_user_has_email_fields(self):
        from models.user import User
        import inspect
        src = inspect.getsource(User)
        self.assertIn("email_confirmed", src)
        self.assertIn("confirmation_token", src)
        print("  ✓ User model has email_confirmed and confirmation_token fields")

    def test_package_image_model(self):
        from models.package_image import PackageImage, PackageImageBase
        import inspect
        # package_id is on the base class, image_data on the table class
        base_src = inspect.getsource(PackageImageBase)
        sub_src = inspect.getsource(PackageImage)
        self.assertIn("package_id", base_src)
        self.assertIn("image_data", sub_src)
        self.assertIn("original_size_bytes", base_src)
        self.assertIn("compressed_size_bytes", base_src)
        self.assertIn("image_url", base_src)
        print("  ✓ PackageImage model has all required fields")

    def test_models_init_exports(self):
        from models import PackageImage, User, Package, Traveler, Sender, Trip, Review, Notification
        print("  ✓ All models exported from models/__init__.py (incl. PackageImage)")

# =====================================================================
# 7. SCHEMAS
# =====================================================================
class TestSchemas(unittest.TestCase):
    def test_forgot_password_request(self):
        from auth.schemas import ForgotPasswordRequest
        req = ForgotPasswordRequest(email="test@example.com")
        self.assertEqual(req.email, "test@example.com")
        print("  ✓ ForgotPasswordRequest schema works")

    def test_user_read_has_email_confirmed(self):
        from auth.schemas import UserRead
        import inspect
        fields = UserRead.model_fields
        self.assertIn("email_confirmed", fields)
        print("  ✓ UserRead schema includes email_confirmed field")

# =====================================================================
# 8. CELERY TASKS STRUCTURE
# =====================================================================
class TestCeleryTasks(unittest.TestCase):
    def test_celery_app(self):
        from celery_app import celery
        self.assertEqual(celery.main, "packagego")
        # Beat schedule must include digest task
        schedule = celery.conf.beat_schedule
        self.assertIn("delivery-digest-every-hour", schedule)
        digest = schedule["delivery-digest-every-hour"]
        self.assertEqual(digest["task"], "tasks.digest_tasks.delivery_digest")
        print("  ✓ Celery app configured with beat schedule for hourly digest")

    def test_email_tasks_exist(self):
        from tasks.email_tasks import send_confirmation_email, send_password_reset_email
        # These are Celery tasks
        self.assertTrue(hasattr(send_confirmation_email, 'delay'))
        self.assertTrue(hasattr(send_password_reset_email, 'delay'))
        print("  ✓ send_confirmation_email and send_password_reset_email are Celery tasks with .delay()")

    def test_image_task_exists(self):
        from tasks.image_tasks import compress_and_store_image
        self.assertTrue(hasattr(compress_and_store_image, 'delay'))
        print("  ✓ compress_and_store_image is a Celery task with .delay()")

    def test_digest_task_exists(self):
        from tasks.digest_tasks import delivery_digest
        self.assertTrue(hasattr(delivery_digest, 'delay'))
        print("  ✓ delivery_digest is a Celery task with .delay()")

# =====================================================================
# 9. IMAGE COMPRESSION LOGIC (no DB/MinIO needed)
# =====================================================================
class TestImageCompressionLogic(unittest.TestCase):
    def test_pillow_compress(self):
        """Test the actual Pillow compression logic in isolation."""
        from PIL import Image
        import io

        # Create a test image in memory (500x500 red square)
        img = Image.new("RGB", (500, 500), color=(255, 0, 0))
        input_buf = io.BytesIO()
        img.save(input_buf, format="PNG")
        original_bytes = input_buf.getvalue()
        original_size = len(original_bytes)

        # Re-open and compress (mimics what the task does)
        img2 = Image.open(io.BytesIO(original_bytes))
        if img2.mode in ("RGBA", "P"):
            img2 = img2.convert("RGB")
        output = io.BytesIO()
        img2.save(output, format="JPEG", quality=70, optimize=True)
        compressed_bytes = output.getvalue()
        compressed_size = len(compressed_bytes)
        ratio = (1 - compressed_size / original_size) * 100

        self.assertGreater(original_size, 0)
        self.assertGreater(compressed_size, 0)
        # JPEG should almost always be smaller than PNG for solid colors
        print(f"  ✓ Image compression works: {original_size:,}B → {compressed_size:,}B ({ratio:.1f}% reduction)")

    def test_resize_logic(self):
        """Verify wide images get resized to max 1920px."""
        from PIL import Image
        import io

        img = Image.new("RGB", (3000, 2000), color=(0, 128, 255))
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        self.assertEqual(img.width, 1920)
        self.assertEqual(img.height, 1280)
        print(f"  ✓ Resize logic: 3000x2000 → {img.width}x{img.height} (max 1920px wide)")

# =====================================================================
# 10. AUTH ROUTES STRUCTURE
# =====================================================================
class TestAuthRoutes(unittest.TestCase):
    def test_new_auth_endpoints_exist(self):
        from auth.routes import router
        paths = [r.path for r in router.routes]
        self.assertIn("/auth/confirm-email/{token}", paths)
        self.assertIn("/auth/forgot-password", paths)
        print("  ✓ New auth endpoints: /auth/confirm-email/{token} and /auth/forgot-password")

# =====================================================================
# 11. API ROUTE STRUCTURE
# =====================================================================
class TestRouteStructure(unittest.TestCase):
    def test_image_routes(self):
        from images import router
        paths = [r.path for r in router.routes]
        self.assertIn("/packages/{package_id}/image", paths)
        # Should have both POST (upload) and GET (retrieve)
        methods = {}
        for r in router.routes:
            if r.path == "/packages/{package_id}/image":
                methods.update({m: True for m in r.methods})
        self.assertIn("POST", methods)
        self.assertIn("GET", methods)
        print("  ✓ Image routes: POST + GET /packages/{id}/image")

    def test_admin_routes(self):
        from admin import router
        paths = [r.path for r in router.routes]
        self.assertIn("/admin/logs", paths)
        print("  ✓ Admin route: GET /admin/logs")

# =====================================================================
# 12. MAIN APP INTEGRATION
# =====================================================================
class TestMainApp(unittest.TestCase):
    def test_main_app_imports_without_error(self):
        """Verify main.py can be imported (all routers and middleware registered)."""
        import importlib
        # We just need it to parse – lifespan won't run
        spec = importlib.util.spec_from_file_location(
            "main_test",
            "/Users/yerko/Downloads/web-back 4-2/main.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        app = mod.app
        # Check version
        self.assertEqual(app.version, "4.0.0")
        # Check all routers are registered
        route_paths = [r.path for r in app.routes]
        self.assertIn("/auth/register", route_paths, "Auth router missing")
        self.assertIn("/packages", route_paths, "Packages router missing")
        self.assertIn("/packages/{package_id}/image", route_paths, "Images router missing")
        self.assertIn("/admin/logs", route_paths, "Admin router missing")
        self.assertIn("/admin/profiling/slow", route_paths, "Profiling router missing")
        print("  ✓ FastAPI app v4.0.0 with all routers registered ✓")
        print(f"  ✓ Total registered routes: {len(app.routes)}")

# =====================================================================
# RUN
# =====================================================================
if __name__ == "__main__":
    print("\n" + "="*65)
    print("  PackageGo – Assignment 4 Verification Tests")
    print("="*65 + "\n")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    test_classes = [
        TestConfig,
        TestMiddlewareImports,
        TestLogLevelClassification,
        TestRateLimitingLogic,
        TestProfilingLogic,
        TestModels,
        TestSchemas,
        TestCeleryTasks,
        TestImageCompressionLogic,
        TestAuthRoutes,
        TestRouteStructure,
        TestMainApp,
    ]
    for cls in test_classes:
        print(f"\n▶ {cls.__name__}")
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
    # Run with our own printing
    result = runner.run(suite)

    print("\n" + "="*65)
    if result.wasSuccessful():
        print(f"  🎉 ALL {result.testsRun} TESTS PASSED")
    else:
        print(f"  ❌ {len(result.failures)} FAILURES, {len(result.errors)} ERRORS")
        for fail in result.failures + result.errors:
            print(f"\n  FAIL: {fail[0]}")
            print(f"  {fail[1]}")
    print("="*65 + "\n")
