FROM csbase.registry.cmbchina.cn/paas/cmb-python-3.9.5:latest

WORKDIR /opt/deployments

COPY ./ /opt/deployments/

RUN cd /opt/deployments/ && \
pip install --no-cache-dir -r requirements.txt \
-i  http://central.jaf.cmbchina.cn/artifactory/api/pypi/group-pypi/simple \
--trusted-host central.jaf.cmbchina.cn --retries 10 --timeout 20

EXPOSE 7788

# Start the FastAPI application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7788"]