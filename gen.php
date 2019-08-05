<?php

// please note that i'm fully aware of how terrible this is, however it's way
// simpler than setting up a python server just for this thing

// run python script
exec("python3 gen.py");

// emit image
$path = 'out.png';
$fp = fopen($path, 'rb');
header("Content-Type: image/png");
header("Content-Length: " . filesize($path));
fpassthru($fp);
