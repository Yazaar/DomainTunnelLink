(() => {
    const onNavTargetClick = (event) => {
        const target = event.currentTarget.getAttribute('data-target');
        if (target) {
            document.querySelector(target)?.scrollTo({ behavior: 'smooth' });
        }
    }

    document.querySelectorAll('.nav-links > div[data-target]').forEach((element) => {
        element.addEventListener('click', onNavTargetClick);
    });

    document.querySelector('#request-resource').addEventListener('click', async (element) => {
        if (element.currentTarget.classList.contains('loading')) {
            return;
        }

        const resourceType = document.querySelector('#resource-type').value;
        const resourceItem = document.querySelector('#resource-item').value;
        const resourceCode = document.querySelector('#resource-code').value;

        if (!resourceType || !resourceItem || !resourceCode) {
            return;
        }


        const target = element.currentTarget;
        target.classList.add('loading');

        const timeout = setTimeout(() => {
            target.classList.remove('loading');
        }, 15000);

        try {
            const resp = await fetch('/api/auth-resource', {
                method: 'post',
                body: JSON.stringify({
                    resourceType,
                    resourceItem,
                    resourceCode
                })
            });

            const data = await resp.json();

            const statusMessage = data.statusMessage;

            document.querySelector('#resource-status').innerText = statusMessage;
        } finally {
            setTimeout(() => {
                clearTimeout(timeout);
                target.classList.remove('loading');
            }, 5000);
        }
    });
})();
