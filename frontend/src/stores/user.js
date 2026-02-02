import {defineStore} from "pinia";
import {ref} from "vue";


export const useUserStore = defineStore('user', ()=>{
    const id = ref(0)
    const username = ref('wxb')
    const photo = ref('')
    const profile = ref('')
    const accessToken = ref('')

    function isLogin(){
        return !!accessToken
    }

    function setAccessToken(token){
        accessToken.value = token
    }

    function setUserInfo(data){
        id.value = data.id
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

    }
})