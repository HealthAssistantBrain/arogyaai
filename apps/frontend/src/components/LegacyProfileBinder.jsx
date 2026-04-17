import { useLayoutEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import { getUserProfile } from '../lib/userProfile';

function updateAvatar(wrapper, profile) {
  const image = wrapper.querySelector('img');
  if (image) {
    image.src = profile.avatar;
    image.alt = profile.name;
    image.onerror = () => {
      image.src = profile.fallbackAvatar;
    };
    return;
  }

  const backgroundAvatar = wrapper.querySelector('[style*="backgroundImage"], [style*="background-image"]');
  if (backgroundAvatar) {
    backgroundAvatar.style.backgroundImage = `url("${profile.avatar}")`;
  }
}

function bindProfileWrapper(wrapper, profile, navigate) {
  const textContainer = Array.from(wrapper.querySelectorAll('div')).find((element) => {
    const className = typeof element.className === 'string' ? element.className : '';
    return className.includes('text-right') || className.includes('min-w-0');
  });

  if (!textContainer) {
    return false;
  }

  const lines = textContainer.querySelectorAll('p');
  if (lines[0]) {
    lines[0].textContent = profile.name;
  }
  if (lines[1]) {
    lines[1].textContent = profile.subtitle;
    lines[1].style.display = profile.subtitle ? '' : 'none';
  }

  updateAvatar(wrapper, profile);

  if (typeof wrapper.__profileCleanup === 'function') {
    wrapper.__profileCleanup();
  }

  const handleClick = (event) => {
    event.preventDefault();
    event.stopPropagation();
    navigate(ROUTES.SETTINGS_PROFILE);
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      event.stopPropagation();
      navigate(ROUTES.SETTINGS_PROFILE);
    }
  };

  wrapper.addEventListener('click', handleClick, true);
  wrapper.addEventListener('keydown', handleKeyDown, true);
  wrapper.__profileCleanup = () => {
    wrapper.removeEventListener('click', handleClick, true);
    wrapper.removeEventListener('keydown', handleKeyDown, true);
  };
  wrapper.setAttribute('role', 'button');
  wrapper.setAttribute('tabindex', '0');

  return true;
}

export default function LegacyProfileBinder() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const role = useAuthStore((state) => state.role);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useLayoutEffect(() => {
    if (!isAuthenticated || location.pathname === ROUTES.DASHBOARD) {
      return;
    }

    const profile = getUserProfile(user, role);
    const frameId = window.requestAnimationFrame(() => {
      const headers = Array.from(document.querySelectorAll('header'));

      headers.forEach((header) => {
        const candidates = Array.from(header.querySelectorAll('div')).filter((element) => {
          const className = typeof element.className === 'string' ? element.className : '';
          if (!className.includes('text-right')) {
            return false;
          }

          const wrapper = element.parentElement;
          if (!wrapper) {
            return false;
          }

          return Boolean(
            wrapper.querySelector('img') ||
            wrapper.querySelector('[style*="backgroundImage"], [style*="background-image"]')
          );
        });

        candidates.forEach((textBlock) => {
          const wrapper = textBlock.parentElement;
          if (wrapper) {
            bindProfileWrapper(wrapper, profile, navigate);
          }
        });
      });

      const sidebarCard = document.querySelector('aside [data-app-sidebar-profile]');
      if (sidebarCard) {
        bindProfileWrapper(sidebarCard, profile, navigate);
      }
    });

    return () => window.cancelAnimationFrame(frameId);
  }, [isAuthenticated, location.pathname, navigate, role, user]);

  return null;
}
