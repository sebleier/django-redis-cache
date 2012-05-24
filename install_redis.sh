if [ -z $REDIS_VERSION ]; then
    echo "This script is used to install redis for Travis-CI"
else
    cd ..
    git clone https://github.com/antirez/redis.git
    cd redis
    git checkout $REDIS_VERSION
    make
fi