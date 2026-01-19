import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="function")
def context(playwright):
    """Creates a new browser context for each test."""
    browser = playwright.chromium.launch()
    context = browser.new_context()
    yield context
    browser.close()

def test_toast_notification(context):
    """Verify toast notifications appear correctly."""
    page = context.new_page()
    
    # We can inject the Toast system directly into a blank page for unit testing
    # since we don't have the full Flask app running in this test environment easily.
    # Alternatively, if the app is running (which it is on port 5000), we can hit it.
    
    try:
        page.goto("http://192.168.155.226:5000")
        page.wait_for_load_state("networkidle")
    except:
        pytest.skip("Server not running at http://192.168.155.226:5000")

    # Inject a test toast trigger
    page.evaluate("""
        window.showToast("Test Success Message", "success");
    """)

    # Verify Toast Appears
    toast = page.locator(".toast.success")
    expect(toast).to_be_visible()
    expect(toast).to_contain_text("Test Success Message")
    
    # Verify icon exists
    expect(toast.locator(".toast-icon")).to_be_visible()
    
    # Verify it disappears (wait > 3s)
    page.wait_for_timeout(3500)
    expect(toast).not_to_be_visible()

def test_toast_variants(context):
    """Verify different toast types."""
    page = context.new_page()
    try:
        page.goto("http://192.168.155.226:5000")
        page.wait_for_load_state("networkidle")
    except:
        pytest.skip("Server not running")

    # Error Toast
    page.evaluate("""window.showToast("Test Error", "error")""")
    error_toast = page.locator(".toast.error")
    expect(error_toast).to_be_visible()
    
    # Info Toast
    page.evaluate("""window.showToast("Test Info", "info")""")
    info_toast = page.locator(".toast.info")
    expect(info_toast).to_be_visible()

def test_aria_navigation(context):
    """Verify accessibility labels on navigation."""
    page = context.new_page()
    try:
        page.goto("http://192.168.155.226:5000")
        page.wait_for_load_state("networkidle")
    except:
        pytest.skip("Server not running")

    # Check Header ARIA
    header = page.locator("header[role='banner']")
    expect(header).to_be_visible()
    
    # Check Nav Links ARIA
    dashboard_link = page.locator("a[aria-label='Dashboard']")
    expect(dashboard_link).to_be_visible()
    
    help_link = page.locator("a[aria-label='Help & Documentation']")
    expect(help_link).to_be_visible()

    # Check Status ARIA
    status_area = page.locator("div[role='status']")
    if status_area.is_visible():
        expect(page.locator("#piTemp[aria-label='CPU Temperature']")).to_be_visible()

if __name__ == "__main__":
    # Allow running directly provided the app is up
    pass
