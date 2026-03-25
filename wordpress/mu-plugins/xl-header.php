<?php
/**
 * XC Ski Labs — Custom Header
 *
 * Injects branded navigation header into WordPress pages.
 * Hides native Astra theme header, replaces with XC Ski Labs nav.
 *
 * Nav items: RACES, TRAINING PLANS, COACHING, ABOUT
 */

defined('ABSPATH') || exit;

// ── Inject header CSS ────────────────────────────────────────
add_action('wp_head', function () {
    ?>
<style>
/* Hide Astra theme header */
.ast-above-header-wrap,
.ast-main-header-wrap,
.ast-below-header-wrap,
#ast-mobile-header,
.ast-above-header,
.site-header { display: none !important; }

/* XC Ski Labs header */
.xl-header {
    background: #1a2332;
    border-bottom: 3px solid #2b4c7e;
    padding: 0;
    position: sticky;
    top: 0;
    z-index: 999;
}
.xl-header-inner {
    max-width: 900px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
}
.xl-logo {
    font-family: 'Sometype Mono', monospace;
    font-weight: 700;
    font-size: 1.1rem;
    color: #e8edf2;
    text-decoration: none;
    letter-spacing: 0.05em;
}
.xl-logo:hover { color: #5dade2; }
.xl-nav {
    display: flex;
    gap: 24px;
    align-items: center;
    list-style: none;
    margin: 0;
    padding: 0;
}
.xl-nav a {
    font-family: 'Sometype Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    color: #9ca8b8;
    text-decoration: none;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 4px 0;
    border-bottom: 2px solid transparent;
    transition: color 0.2s, border-color 0.2s;
}
.xl-nav a:hover,
.xl-nav a.active {
    color: #e8edf2;
    border-bottom-color: #1b7260;
}
/* Mobile hamburger */
.xl-hamburger {
    display: none;
    background: none;
    border: none;
    color: #e8edf2;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 4px;
}
@media (max-width: 640px) {
    .xl-hamburger { display: block; }
    .xl-nav {
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        right: 0;
        background: #1a2332;
        flex-direction: column;
        padding: 16px 20px;
        gap: 16px;
        border-bottom: 3px solid #2b4c7e;
    }
    .xl-nav.open { display: flex; }
}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
    <?php
}, 5);

// ── Inject header HTML ───────────────────────────────────────
add_action('wp_body_open', function () {
    $path = $_SERVER['REQUEST_URI'] ?? '';
    $is_races   = (strpos($path, '/search') !== false || strpos($path, '/race/') !== false);
    $is_plans   = (strpos($path, '/training') !== false || strpos($path, '/questionnaire') !== false);
    $is_coach   = (strpos($path, '/coaching') !== false);
    $is_about   = (strpos($path, '/about') !== false);
    ?>
<header class="xl-header">
    <div class="xl-header-inner">
        <a href="/" class="xl-logo">XC SKI LABS</a>
        <button class="xl-hamburger" onclick="document.querySelector('.xl-nav').classList.toggle('open')" aria-label="Menu">&#9776;</button>
        <nav class="xl-nav">
            <a href="/search/"<?php echo $is_races ? ' class="active"' : ''; ?>>Races</a>
            <a href="/training-plans/"<?php echo $is_plans ? ' class="active"' : ''; ?>>Training Plans</a>
            <a href="/coaching/apply/"<?php echo $is_coach ? ' class="active"' : ''; ?>>Coaching</a>
            <a href="/about/"<?php echo $is_about ? ' class="active"' : ''; ?>>About</a>
        </nav>
    </div>
</header>
    <?php
}, 1);

// ── Add body class ───────────────────────────────────────────
add_filter('body_class', function ($classes) {
    $classes[] = 'xl-neo-brutalist-page';
    return $classes;
});
