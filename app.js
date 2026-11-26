document.addEventListener("DOMContentLoaded", function () {
  var menuButton = document.querySelector(".menu-toggle");
  var navigation = document.querySelector(".primary-nav");

  if (menuButton && navigation) {
    menuButton.addEventListener("click", function () {
      var isOpen = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!isOpen));
      navigation.classList.toggle("nav-open", !isOpen);
    });
  }

  var locationButton = document.querySelector("[data-location-button]");
  var locationStatus = document.querySelector("[data-location-status]");
  if (locationButton && locationStatus) {
    locationButton.addEventListener("click", function () {
      if (!navigator.geolocation) {
        locationStatus.textContent = "Location permission is not available in this browser.";
        return;
      }
      locationStatus.textContent = "Waiting for your permission…";
      navigator.geolocation.getCurrentPosition(
        function () {
          locationStatus.textContent = "Location permission granted on this device. GPS-distance search is not enabled yet.";
        },
        function () {
          locationStatus.textContent = "Location was not shared. You can search by area or PIN code instead.";
        },
        { timeout: 10000 }
      );
    });
  }
});
