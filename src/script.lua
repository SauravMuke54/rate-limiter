local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

redis.call("ZREMRANGEBYSCORE", key, 0, now - window * 1000)
local current = redis.call("ZCARD", key)

if current < limit then
    redis.call("ZADD", key, now, now)
    redis.call("PEXPIRE", key, window * 1000)
end

local ttl = redis.call("PTTL", key)
return {current + 1, ttl}