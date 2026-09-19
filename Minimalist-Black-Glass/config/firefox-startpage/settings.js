
    var ghStoreKey = 'sp_gh';
    var ghUserEl = document.getElementById('ghUser');
    var ghStatus = document.getElementById('ghStatus');
    var ghSave = document.getElementById('ghSave');
    var ghCancel = document.getElementById('ghCancel');

    function goHome() { location.href = 'startpage.html'; }

    function showStatus(msg, isError) {
      ghStatus.textContent = msg;
      ghStatus.style.borderLeftColor = isError ? '#ff3750' : '#ffffff';
      ghStatus.style.color = isError ? '#ff3750' : '#8a8a8a';
    }

    function loadSaved() {
      try {
        var saved = localStorage.getItem(ghStoreKey);
        if (saved) ghUserEl.value = saved;
      } catch (e) {}
    }

    function save() {
      var username = ghUserEl.value.trim();
      if (!username) {
        showStatus('Please enter a GitHub username', true);
        ghUserEl.focus();
        return;
      }

      if (!/^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$/i.test(username)) {
        showStatus('Invalid username. Use letters, numbers, hyphens (not at start/end).', true);
        ghUserEl.focus();
        return;
      }

      ghStatus.textContent = 'Saving...';
      ghSave.disabled = true;
      ghSave.textContent = 'SAVING...';

      fetch('https://api.github.com/users/' + encodeURIComponent(username))
        .then(function(r) {
          if (r.status === 404) throw new Error('User not found');
          if (r.status === 403 || r.status === 429) throw new Error('Rate limited');
          if (!r.ok) throw new Error('Error ' + r.status);
          return r.json();
        })
        .then(function(d) {
          try {
            localStorage.setItem(ghStoreKey, d.login);
          } catch (e) {}
          showStatus('Saved! Returning to startpage...');
          setTimeout(goHome, 1200);
        })
        .catch(function(err) {
          showStatus('Error: ' + (err && err.message || err), true);
        })
        .finally(function() {
          ghSave.disabled = false;
          ghSave.textContent = 'SAVE';
        });
    }

    ghSave.addEventListener('click', save);
    ghCancel.addEventListener('click', goHome);
    ghUserEl.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') { e.preventDefault(); save(); }
      else if (e.key === 'Escape') { goHome(); }
    });

    loadSaved();
  