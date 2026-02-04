import {defineStore} from "pinia";
import {ref} from "vue";


export const useUserStore = defineStore('user', ()=>{
    const id = ref(0)
    const username = ref('')
    const photo = ref('')
    const profile = ref('')
    const accessToken = ref('')
    const hasPulledUserInfo = ref(false)

    function setPulledUserInfo(newStatus){
        hasPulledUserInfo.value = newStatus
    }

    function isLogin(){
        return !!accessToken.value
    }

    function setAccessToken(token){
        accessToken.value = token
        // console.log('成功修改token'+token)
    }

    function setUserInfo(data){
        id.value = data.user_id
        username.value = data.username
        photo.value = data.photo
        profile.value = data.profile

    }

    function logout(){
        id.value = 0
        username.value = ''
        photo.value = ''
        profile.value = ''
        accessToken.value = ''
    }

    return {
        id,
        username,
        photo,
        profile,
        accessToken,
        isLogin,
        logout,
        setUserInfo,
        setAccessToken,
        hasPulledUserInfo,
        setPulledUserInfo,
    }
})