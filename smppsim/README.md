# 📌 NOTE

Jasmin comes with a default SMPP SMSC server.

However, we've included an additional SMPP server called **`smppsim`** for enhanced testing.

You'll find it in the project directory under the folder: `smppsim/`

---

## 📁 Folder Contents

- **`Dockerfile`**  
  Used to build the `smppsim` Docker image. This image is automatically used to spin up the service via `docker-compose.yml`.

- **`entrypoint.sh`**  
  Script executed inside the Docker container to start the SMPP server.

- **`smppsim.jar`**  
  The Java JAR file that runs the SMPP simulator server.

- **`conf/`** (configuration folder)  
  Contains the following configuration files:
  - `logging.properties` — Logging configuration.
  - `smppsim.props` — SMPP server settings (e.g., port, bind credentials, etc.).

These config files are used in the `entrypoint.sh` script to start the server using:

```bash
java -Djava.net.preferIPv4Stack=true \
     -Djava.util.logging.config.file=conf/logging.properties \
     -jar ./smppsim.jar conf/smppsim.props
```

## ⚙️ Integration with Jasmin
Everything is automated. Just make sure your test Jasmin smppccm connector is mapped correctly to the smppsim server.

**Important:** from Jasmin (Docker), the connector host must be the compose service name `smppsim`, not `localhost`.

Here's an example setup for the connector:

```bash
smppccm -a
> cid smppsim-connector
> host smppsim
> port 2776
> username smppclient1
> password password
> src_ton 1
> src_npi 1
> dst_ton 1
> dst_npi 1
> bind_ton 1
> bind_npi 1
> bind transceiver
> submit_throughput 110
> ok
```

### Testing MO (Mobile Originated)

Compose publishes:

- `2776` — SMPP
- `88` — SMPPSim web UI

1. Start Jasmin’s SMPP connector (bound/transceiver to `smppsim:2776`).
2. Open **http://localhost:88/inject_mo.htm**
3. Submit a message — SMPPSim queues a `deliver_sm` to Jasmin.
4. Confirm in Jasmin logs / your MO HTTP route callback.

Static pages live under `smppsim/www/` (copied into the image as `DOCROOT=www`).

### Dependencies
`smppsim.jar` expects `lib/jakarta-regexp-1.5.jar` (and stubs for `junit.jar` / `smpp.jar`) on the classpath. The Dockerfile copies `smppsim/lib/` into the image for this.
