/**
 * E2E: Navigation & Theme Toggle
 * Stream 5.1 — Frontend QA
 * 
 * Verifies all main navigation routes load without errors
 * and dark mode can be toggled.
 */
import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('dashboard loads and shows heading', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toBeVisible();
  });

  test('settings page loads', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByText('System Configuration')).toBeVisible();
  });

  test('tap list page loads', async ({ page }) => {
    await page.goto('/taplist');
    await expect(page.getByText('On Tap')).toBeVisible();
  });

  test('automation page loads with tabs', async ({ page }) => {
    await page.goto('/automation');
    await expect(page.getByText('Automation & AI')).toBeVisible();
    await expect(page.getByText('Inventory Sync')).toBeVisible();
    await expect(page.getByText('Sourcing Agent')).toBeVisible();
    await expect(page.getByText('Monte Carlo R&D')).toBeVisible();
  });

  test('kiosk page loads in dark mode', async ({ page }) => {
    await page.goto('/kiosk');
    // Kiosk should have black background
    const body = page.locator('div.fixed');
    await expect(body).toHaveCSS('background-color', 'rgb(0, 0, 0)');
  });

  test('legacy dashboard is still accessible', async ({ page }) => {
    await page.goto('/legacy');
    // Should load without a 404
    await expect(page).not.toHaveURL(/404/);
  });
});

test.describe('Theme Toggle', () => {
  test('clicking theme toggle adds dark class to html element', async ({ page }) => {
    await page.goto('/');
    
    // Find and click the theme toggle button
    const toggleButton = page.getByRole('button', { name: /toggle theme/i }).first();
    await toggleButton.click();
    
    // Verify the html element received the .dark class
    const htmlEl = page.locator('html');
    await expect(htmlEl).toHaveClass(/dark/);
    
    // Click again to toggle back
    await toggleButton.click();
    await expect(htmlEl).not.toHaveClass(/dark/);
  });
});
