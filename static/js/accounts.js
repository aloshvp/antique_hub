/**
 * Antique Hub - Accounts & Cascading Dropdowns JS
 * Handles:
 * 1. State -> District -> Location dynamic cascading dropdowns via Fetch API
 * 2. Real-time DFD "Check Existing" AJAX validation for Username & Email
 */

document.addEventListener('DOMContentLoaded', function () {
    const stateSelect = document.getElementById('id_state');
    const districtSelect = document.getElementById('id_district');
    const locationSelect = document.getElementById('id_location');

    // -------------------------------------------------------------
    // 1. Cascading Dropdown: State -> District
    // -------------------------------------------------------------
    if (stateSelect && districtSelect) {
        stateSelect.addEventListener('change', function () {
            const stateId = this.value;
            districtSelect.innerHTML = '<option value="">-- Loading Districts... --</option>';
            if (locationSelect) {
                locationSelect.innerHTML = '<option value="">-- Select Location --</option>';
            }

            if (!stateId) {
                districtSelect.innerHTML = '<option value="">-- Select District --</option>';
                return;
            }

            fetch(`/locations/ajax/load-districts/?state_id=${encodeURIComponent(stateId)}`)
                .then(response => response.json())
                .then(data => {
                    districtSelect.innerHTML = '<option value="">-- Select District --</option>';
                    if (data.districts && data.districts.length > 0) {
                        data.districts.forEach(d => {
                            const option = document.createElement('option');
                            option.value = d.distid;
                            option.textContent = d.dist;
                            districtSelect.appendChild(option);
                        });
                    } else {
                        districtSelect.innerHTML = '<option value="">-- No Districts Found --</option>';
                    }
                })
                .catch(err => {
                    console.error('Error loading districts:', err);
                    districtSelect.innerHTML = '<option value="">-- Error loading districts --</option>';
                });
        });
    }

    // -------------------------------------------------------------
    // 2. Cascading Dropdown: District -> Location
    // -------------------------------------------------------------
    if (districtSelect && locationSelect) {
        districtSelect.addEventListener('change', function () {
            const districtId = this.value;
            locationSelect.innerHTML = '<option value="">-- Loading Locations... --</option>';

            if (!districtId) {
                locationSelect.innerHTML = '<option value="">-- Select Location --</option>';
                return;
            }

            fetch(`/locations/ajax/load-locations/?district_id=${encodeURIComponent(districtId)}`)
                .then(response => response.json())
                .then(data => {
                    locationSelect.innerHTML = '<option value="">-- Select Location --</option>';
                    if (data.locations && data.locations.length > 0) {
                        data.locations.forEach(loc => {
                            const option = document.createElement('option');
                            option.value = loc.locid;
                            option.textContent = loc.locname;
                            locationSelect.appendChild(option);
                        });
                    } else {
                        locationSelect.innerHTML = '<option value="">-- No Locations Found --</option>';
                    }
                })
                .catch(err => {
                    console.error('Error loading locations:', err);
                    locationSelect.innerHTML = '<option value="">-- Error loading locations --</option>';
                });
        });
    }

    // -------------------------------------------------------------
    // 3. Real-Time DFD Step: 'Check Existing' (Username & Email)
    // -------------------------------------------------------------
    function setupCheckExisting(inputId, feedbackId, fieldType) {
        const inputElem = document.getElementById(inputId);
        const feedbackElem = document.getElementById(feedbackId);

        if (!inputElem || !feedbackElem) return;

        inputElem.addEventListener('blur', function () {
            const val = this.value.trim();
            if (val.length < 3) {
                feedbackElem.textContent = '';
                feedbackElem.className = 'form-text';
                return;
            }

            feedbackElem.textContent = 'Checking availability...';
            feedbackElem.className = 'form-text text-muted';

            fetch(`/ajax/check-existing/?field=${fieldType}&value=${encodeURIComponent(val)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.exists) {
                        feedbackElem.textContent = `❌ ${data.message}`;
                        feedbackElem.className = 'form-text text-danger fw-semibold';
                        inputElem.classList.add('is-invalid');
                        inputElem.classList.remove('is-valid');
                    } else {
                        feedbackElem.textContent = `✓ ${data.message}`;
                        feedbackElem.className = 'form-text text-success fw-semibold';
                        inputElem.classList.remove('is-invalid');
                        inputElem.classList.add('is-valid');
                    }
                })
                .catch(err => {
                    console.error(`Error checking ${fieldType}:`, err);
                });
        });
    }

    setupCheckExisting('id_username', 'username-feedback', 'username');
    setupCheckExisting('id_email', 'email-feedback', 'email');
});
