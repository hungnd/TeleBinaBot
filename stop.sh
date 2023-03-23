ps aux | grep -ie telebina | awk '{print $2}' | xargs kill -9
