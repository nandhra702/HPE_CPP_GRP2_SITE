(function () {
    function getDocHeight() {
        var D = document;
        return Math.max(
            Math.max(D.body.scrollHeight, D.documentElement.scrollHeight),
            Math.max(D.body.offsetHeight, D.documentElement.offsetHeight),
            Math.max(D.body.clientHeight, D.documentElement.clientHeight)
        );
    }
    function getDocWidth() {
        var D = document;
        return Math.max(
            Math.max(D.body.scrollWidth, D.documentElement.scrollWidth),
            Math.max(D.body.offsetWidth, D.documentElement.offsetWidth),
            Math.max(D.body.clientWidth, D.documentElement.clientWidth)
        );
    }
    function next(elem) {
        // Credit to John Resig for this function
        // taken from Pro JavaScript techniques
        do {
            elem = elem.nextSibling;
        } while (elem && elem.nodeType != 1);
        return elem;
    }
    function prev(elem) {
        // Credit to John Resig for this function
        // taken from Pro JavaScript techniques
        do {
            elem = elem.previousSibling;
        } while (elem && elem.nodeType != 1);
        return elem;
    }
    function redraw(element) {
        element = $(element);
        var n = document.createTextNode(' ');
        element.appendChild(n);
        (function () {
            n.parentNode.removeChild(n)
        }).defer();
        return element;
    }
    function minimizeMaximize(widget, main_block, editor) {
        if (window.fullscreen == true) {
            main_block.className = 'django-ace-editor';
            widget.style.width = window.ace_widget.width + 'px';
            widget.style.height = window.ace_widget.height + 'px';
            window.fullscreen = false;
        }
        else {
            window.ace_widget = {
                'width': widget.offsetWidth,
                'height': widget.offsetHeight
            };
            main_block.className = 'django-ace-editor-fullscreen';
            widget.style.height = getDocHeight() + 'px';
            widget.style.width = getDocWidth() + 'px';
            window.scrollTo(0, 0);
            window.fullscreen = true;
        }
        editor.resize();
    }
    function apply_widget(widget) {
        var div = widget.firstChild,
            textarea = next(widget),
            editor = ace.edit(div),
            mode = widget.getAttribute('data-mode'),
            theme = widget.getAttribute('data-theme'),
            wordwrap = widget.getAttribute('data-wordwrap'),
            toolbar = prev(widget),
            main_block = toolbar.parentNode;
            toolbar = (function findToolbar(elem) {
                while (elem = elem.previousSibling) {
                    if (elem.nodeType === 1 && elem.classList.contains('django-ace-toolbar')) {
                        return elem;
                    }
                }
                return null;
            })(widget),
            main_block = toolbar ? toolbar.parentNode : null;

        // Toolbar maximize/minimize button
        var min_max = toolbar.getElementsByClassName('django-ace-max_min');
        min_max[0].onclick = function () {
            minimizeMaximize(widget, main_block, editor);
            return false;
        };
        if (toolbar) {
            var min_max = toolbar.getElementsByClassName('django-ace-max_min');
            if (min_max.length > 0) {
                min_max[0].onclick = function () {
                    minimizeMaximize(widget, main_block, editor);
                    return false;
                };
            }
            // Add custom copy and paste buttons to the toolbar
            addCustomCopyPasteButtons(toolbar, editor);
        }

        editor.getSession().setValue(textarea.value);

        // the editor is initially absolute positioned
        textarea.style.display = "none";
        // options
        if (mode) {
            editor.getSession().setMode('ace/mode/' + mode);
        }
        if (theme) {
            editor.setTheme("ace/theme/" + theme);
        }
        if (wordwrap == "true") {
            editor.getSession().setUseWrapMode(true);
        }
        editor.getSession().on('change', function () {
            textarea.value = editor.getSession().getValue();
        });
        editor.commands.addCommands([
            {
                name: 'Full screen',
                bindKey: {win: 'Ctrl-F11', mac: 'Command-F11'},
                exec: function (editor) {
                    minimizeMaximize(widget, main_block, editor);
                },
                readOnly: true // false if this command should not apply in readOnly mode
            },
            {
                name: 'submit',
                bindKey: {win: 'Ctrl+Enter', mac: 'Command+Enter'},
                exec: function (editor) {
                    $('form#problem_submit').submit();
                },
                readOnly: true
            },
            {
                name: "showKeyboardShortcuts",
                bindKey: {win: "Ctrl-Shift-/", mac: "Command-Shift-/"},
                exec: function (editor) {
                    ace.config.loadModule("ace/ext/keybinding_menu", function (module) {
                        module.init(editor);
                        editor.showKeyboardShortcuts();
                    });
                }
            },
            {
                name: "increaseFontSize",
                bindKey: "Ctrl-+",
                exec: function (editor) {
                    var size = parseInt(editor.getFontSize(), 10) || 12;
                    editor.setFontSize(size + 1);
                }
            },
            {
                name: "decreaseFontSize",
                bindKey: "Ctrl+-",
                exec: function (editor) {
                    var size = parseInt(editor.getFontSize(), 10) || 12;
                    editor.setFontSize(Math.max(size - 1 || 1));
                }
            },
            {
                name: "resetFontSize",
                bindKey: "Ctrl+0",
                exec: function (editor) {
                    editor.setFontSize(12);
                }
            }
        ]);
        window[widget.id] = editor;
        $(widget).trigger('ace_load', [editor]);
    }
    function init() {
        var widgets = document.getElementsByClassName('django-ace-widget');
        for (var i = 0; i < widgets.length; i++) {
            var widget = widgets[i];
            widget.className = "django-ace-widget"; // remove `loading` class
            apply_widget(widget);
        }
    }
    if (window.addEventListener) { // W3C
        window.addEventListener('load', init);
    } else if (window.attachEvent) { // Microsoft
        window.attachEvent('onload', init);
    }
})();

document.addEventListener('copy', function(e) {
    alert('Copy is disabled.');
    e.preventDefault();
});
document.addEventListener('cut', function(e) {
    alert('Cut is disabled.');
    e.preventDefault();
});
document.addEventListener('paste', function(e) {
    alert('Paste is disabled.');
    e.preventDefault();
});
document.addEventListener('contextmenu', function(e) {
    alert('Right-click is disabled.');
    e.preventDefault();
});
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'C', 'V', 'X'].includes(e.key)) {
        alert('Copy, cut, and paste shortcuts are disabled.');
        e.preventDefault();
    }
});

console.log('Custom [widget.js](http://_vscodecontentref_/5) loaded');

function addCustomCopyPasteButtons(toolbar, editor) {
    // Create Copy button
    var copyBtn = document.createElement('button');
    copyBtn.id = 'customCopyBtn';
    copyBtn.textContent = 'Copy';
    copyBtn.className = 'custom-copy-paste-btn';
    copyBtn.onclick = function(event) {
        event.preventDefault(); // prevent any default action like form submit or reload
        window.tempClipboard = editor.getSelectedText();
        sessionStorage.setItem('tempClipboard', window.tempClipboard);
        console.log('Copied to temporary clipboard:', window.tempClipboard);
        // alert('Copied to temporary clipboard!');
    };

    // Create Paste button
    var pasteBtn = document.createElement('button');
    pasteBtn.id = 'customPasteBtn';
    pasteBtn.textContent = 'Paste';
    pasteBtn.className = 'custom-copy-paste-btn';
    pasteBtn.onclick = function(event) {
        event.preventDefault();
        var clipboardData = window.tempClipboard || sessionStorage.getItem('tempClipboard');
        if (clipboardData) {
            editor.insert(clipboardData);
            window.tempClipboard = "";
            sessionStorage.removeItem('tempClipboard');
            console.log('Pasted from temporary clipboard');
            // alert('Pasted from temporary clipboard!');
        } else {
            console.log('Clipboard is empty!');
            // alert('Clipboard is empty!');
        }
    };

    // Add buttons to toolbar
    toolbar.appendChild(copyBtn);
    toolbar.appendChild(pasteBtn);
}

// Removed local tempClipboard variable to avoid confusion

// Optionally, block default copy/paste everywhere
document.addEventListener('copy', function(e) { e.preventDefault(); });
document.addEventListener('paste', function(e) { e.preventDefault(); });