// Debloated & minimal user.js - applied on every Firefox start
user_pref("browser.ml.chat.enabled", false);
user_pref("browser.ml.chat.sidebar.enabled", false);
user_pref("browser.ml.chat.selection.enabled", false);
user_pref("browser.ml.chat.summarizer", false);
user_pref("browser.shopping.experience2023.enabled", false);
user_pref("browser.shopping.experience2024.enabled", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);
user_pref("browser.newtabpage.activity-stream.feeds.snippets", false);
user_pref("browser.newtabpage.activity-stream.section.highlights.includePocket", false);
user_pref("browser.discovery.enabled", false);
user_pref("browser.ping-centre.telemetry", false);
user_pref("browser.urlbar.suggest.searches", true);
user_pref("browser.urlbar.suggest.topsites", false);
user_pref("browser.urlbar.quicksuggest.enabled", false);
user_pref("browser.urlbar.quicksuggest.spocEnabled", false);
user_pref("browser.urlbar.suggest.quicksuggest.sponsored", false);
user_pref("browser.urlbar.suggest.quicksuggest.nonsponsored", false);
user_pref("browser.urlbar.contextualSearch.enabled", false);
user_pref("browser.urlbar.quickactions.enabled", false);
user_pref("browser.search.suggest.enabled", true);
user_pref("toolkit.telemetry.enabled", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("app.normandy.enabled", false);
user_pref("browser.vpn_promos.enabled", false);
user_pref("browser.privatebrowsing.vpnpromourl", "");
user_pref("identity.fxaccounts.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("browser.tabs.firefox-view", false);
user_pref("browser.toolbars.bookmarks.visibility", "never");

// JetBrains Mono fallback for pages that specify no font
user_pref("browser.display.use_document_fonts", 1);
user_pref("font.default.x-western", "sans-serif");
user_pref("font.name.sans-serif.x-western", "JetBrainsMono Nerd Font");
user_pref("font.name.serif.x-western", "JetBrainsMono Nerd Font");
user_pref("font.name.monospace.x-western", "JetBrainsMono Nerd Font");

// Startup page - new startpage.html
// Let userChrome.css / userContent.css theme the browser chrome
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

user_pref("browser.startup.homepage", "file:///home/yummy.dev/.config/firefox-startpage/startpage.html");

// Toolbar: force Passwords (logins-button) + Incognito (privatebrowsing-button) into the nav-bar
user_pref("browser.uiCustomization.state", "{\"placements\":{\"widget-overflow-fixed-list\":[],\"unified-extensions-area\":[\"emoji_saveriomorelli_com-browser-action\",\"authenticator_mymindstorm-browser-action\",\"notesidebar_stefanvd_net-browser-action\",\"_c2c003ee-bd69-42a2-b0e9-6f34222cb046_-browser-action\",\"_edfc63b3-fc9b-4b6b-b9bf-4561ad548044_-browser-action\"],\"nav-bar\":[\"back-button\",\"forward-button\",\"reload-button\",\"stop-button\",\"vertical-spacer\",\"urlbar-container\",\"downloads-button\",\"logins-button\",\"privatebrowsing-button\",\"ipprotection-button\",\"fxa-toolbar-menu-button\",\"reset-pbm-toolbar-button\",\"unified-extensions-button\"],\"toolbar-menubar\":[\"menubar-items\"],\"TabsToolbar\":[\"tabbrowser-tabs\",\"new-tab-button\",\"customizableui-special-spring3\",\"alltabs-button\",\"ai-window-toggle\"],\"vertical-tabs\":[],\"PersonalToolbar\":[\"personal-bookmarks\"]},\"seen\":[\"reset-pbm-toolbar-button\",\"emoji_saveriomorelli_com-browser-action\",\"authenticator_mymindstorm-browser-action\",\"notesidebar_stefanvd_net-browser-action\",\"_c2c003ee-bd69-42a2-b0e9-6f34222cb046_-browser-action\",\"_edfc63b3-fc9b-4b6b-b9bf-4561ad548044_-browser-action\",\"ai-window-toggle\",\"ipprotection-button\",\"screenshot-button\",\"developer-button\",\"logins-button\",\"privatebrowsing-button\"],\"dirtyAreaCache\":[\"unified-extensions-area\",\"nav-bar\",\"toolbar-menubar\",\"TabsToolbar\",\"vertical-tabs\",\"PersonalToolbar\"],\"currentVersion\":26,\"newElementCount\":4}");
user_pref("signon.rememberSignons", true);

// Toolbar layout: add Passwords (logins-button) + Incognito (privatebrowsing-button)
user_pref("widget.use-xdg-desktop-portal.file-picker", 1);
