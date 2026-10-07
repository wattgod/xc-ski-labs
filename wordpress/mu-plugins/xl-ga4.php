<?php
/**
 * XC Ski Labs — GA4 Analytics
 *
 * Injects Google Analytics 4 tracking snippet into <head>.
 * Skips for logged-in admins/editors.
 *
 * Measurement ID: G-3JQLSQLPPM (XC Ski Labs property)
 */

defined('ABSPATH') || exit;

add_action('wp_head', function () {
    // Skip tracking for admins and editors
    if (is_user_logged_in() && current_user_can('edit_posts')) {
        return;
    }

    ?>
<!-- XC Ski Labs GA4 -->
<script src="/xc-assets/analytics.js"></script>
<!-- /XC Ski Labs GA4 -->
    <?php
}, 1);
