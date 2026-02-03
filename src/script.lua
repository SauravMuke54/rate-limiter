local key = KEYS[1]
local limit = ARGV[1]

local current = redis.call("INCR", key)

if current == 1 then
    redis.call("EXPIRE", key, limit)
end

local ttl = redis.call("TTL", key)

return {current, ttl}