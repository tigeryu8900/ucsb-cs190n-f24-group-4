const http = require("node:http");
const net = require("node:net");

const server = http.createServer((client_req, client_res) => {
  try {
    const urlObj = new URL(client_req.url ?? "");
    const target = urlObj.protocol + "//" + urlObj.host;
    console.log("Proxying HTTP request for:", target);

    const options = {
      hostname: urlObj.hostname,
      port: urlObj.port ?? 80,
      path: urlObj.pathname,
      method: client_req.method,
      headers: client_req.headers
    };

    const proxy = http.request(options, (res) => {
      client_res.writeHead(res.statusCode ?? 200, res.headers);
      res.pipe(client_res);
    });

    client_req.pipe(proxy);

    client_res.on("error", e => {
      console.error(e);
      proxy.end();
    });

    proxy.on("error", e => {
      console.error(e);
      client_req.destroy()
    });
  } catch (e) {
    console.error(e);
    try {
      client_res.writeHead(500);
    } finally {
      client_res.end();
    }
  }
});

const regex_hostport = /^([^:]+)(:([0-9]+))?$/;

function getHostPortFromString(hostString, defaultPort) {
  let host = hostString;
  let port = defaultPort;

  const result = regex_hostport.exec(hostString);
  if (result != null) {
    host = result[1];
    if (result[2] != null) {
      port = parseInt(result[3]);
    }
  }

  return [host, port];
}

server.on("connect", (client_req, socket, bodyhead) => {
  const [domain, port] = getHostPortFromString(client_req.url ?? "", 443);
  console.log("Proxying HTTPS request for:", domain, port);

  const proxySocket = new net.Socket();
  try {
    proxySocket.connect(port, domain, () => {
      proxySocket.write(bodyhead);
      socket.write(`HTTP/${client_req.httpVersion} 200 Connection established\r\n\r\n`);
    });

    proxySocket.pipe(socket);

    proxySocket.on("error", () => {
      socket.write(`HTTP/${client_req.httpVersion} 500 Connection error\r\n\r\n`);
      socket.end();
    });

    socket.pipe(proxySocket);

    socket.on("error", () => {
      proxySocket.end();
    });
  } catch (e) {
    console.error(e);
    socket.write(`HTTP/${client_req.httpVersion} 500 Connection error\r\n\r\n`);
    socket.end();
  }
});

server.listen(process.env.PORT ?? 18080);
